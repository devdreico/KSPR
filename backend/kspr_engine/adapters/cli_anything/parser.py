"""SKILLParser — parses SKILL.md files with YAML frontmatter into CapabilitySchema."""

from __future__ import annotations

import re

import yaml

from ...capabilities.schemas import CapabilitySchema


class SKILLParser:
    """Parses SKILL.md files (YAML frontmatter + markdown body) into CapabilitySchema."""

    @staticmethod
    def parse_skill_md(skill_path: str) -> CapabilitySchema | None:
        """Parse a SKILL.md file and return a CapabilitySchema."""
        from pathlib import Path

        path = Path(skill_path)
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            return None

        try:
            meta = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None

        body = content[frontmatter_match.end() :]
        commands = SKILLParser._extract_commands_from_tables(body)
        skill_content = content

        return CapabilitySchema(
            id=f"cli-any:{meta.get('name', path.parent.name)}",
            name=meta.get("name", path.parent.name),
            description=meta.get("description", ""),
            source=str(path),
            source_type="cli-anything",
            category=meta.get("category", "utility"),
            command=meta.get("command", []),
            arguments=commands,
            returns_json=meta.get("returns_json", False),
            requires=meta.get("requires", []),
            skill_path=str(path),
            skill_content=skill_content,
            installed=True,
            version=meta.get("version", "0.0.1"),
            metadata=meta.get("metadata", {}),
        )

    @staticmethod
    def _extract_commands_from_tables(body: str) -> dict:
        """Extract commands from markdown tables with backtick code."""
        commands: dict = {}
        row_pattern = re.compile(
            r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", re.MULTILINE
        )

        for match in row_pattern.finditer(body):
            cmd_str = match.group(1).strip()
            description = match.group(2).strip()
            parts = cmd_str.split()
            if parts:
                cmd_name = parts[0]
                args = re.findall(r"<(\w+)>", cmd_str)
                flags = re.findall(r"--(\w[\w-]*)", cmd_str)
                commands[cmd_name] = {
                    "description": description,
                    "usage": cmd_str,
                    "positional_args": args,
                    "flags": flags,
                }

        return commands

    @staticmethod
    def parse_from_string(content: str, name: str = "unknown") -> CapabilitySchema | None:
        """Parse SKILL.md from a string (for testing)."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            return SKILLParser.parse_skill_md(temp_path)
        finally:
            os.unlink(temp_path)
