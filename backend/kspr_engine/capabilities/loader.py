"""CapabilityLoader — loads SKILL.md files and enriches capabilities with CLI --help data."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

from .schemas import CapabilitySchema


class CapabilityLoader:
    """Loads and enriches CapabilitySchema from various sources."""

    @staticmethod
    def load_skill_md(skill_path: str) -> CapabilitySchema | None:
        """Parse a SKILL.md file with YAML frontmatter + markdown body."""
        path = Path(skill_path)
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            return None

        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None

        name = frontmatter.get("name", path.parent.name)
        description = frontmatter.get("description", "")

        body = content[frontmatter_match.end() :]
        commands = CapabilityLoader._parse_markdown_commands(body)

        skill_content = frontmatter_match.group(0) + body

        return CapabilitySchema(
            id=f"skill:{name}",
            name=name,
            description=description,
            source=str(path),
            source_type="cli-anything",
            category=frontmatter.get("category", "utility"),
            command=frontmatter.get("command", []),
            arguments=commands,
            returns_json=frontmatter.get("returns_json", False),
            requires=frontmatter.get("requires", []),
            skill_path=str(path),
            skill_content=skill_content,
            installed=True,
            version=frontmatter.get("version", "0.0.1"),
            metadata=frontmatter.get("metadata", {}),
        )

    @staticmethod
    def _parse_markdown_commands(body: str) -> dict:
        """Extract commands from markdown tables."""
        commands = {}
        table_pattern = re.compile(
            r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", re.MULTILINE
        )
        for match in table_pattern.finditer(body):
            cmd_str = match.group(1).strip()
            desc = match.group(2).strip()
            cmd_name = cmd_str.split()[0] if cmd_str else cmd_str
            commands[cmd_name] = {
                "description": desc,
                "usage": cmd_str,
                "args": re.findall(r"<(\w+)>", cmd_str),
            }
        return commands

    @staticmethod
    def load_cli_help(command: list[str], help_flag: str = "--help") -> dict:
        """Run a CLI with --help and extract basic info."""
        try:
            result = subprocess.run(
                command + [help_flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return {"error": f"Exit code {result.returncode}"}

            output = result.stdout or result.stderr
            lines = [line.strip() for line in output.split("\n") if line.strip()]
            description = lines[0] if lines else ""

            args = re.findall(r"<(\w+)>", output)
            options = re.findall(r"--(\w[\w-]*)", output)

            return {
                "description": description,
                "positional_args": args,
                "options": options,
                "raw_help": output,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Timeout running --help"}
        except FileNotFoundError:
            return {"error": "Command not found"}

    @staticmethod
    def enrich_capability(
        cap: CapabilitySchema,
        cli_help: dict | None = None,
    ) -> CapabilitySchema:
        """Enrich a CapabilitySchema with additional CLI --help data."""
        if cli_help and "error" not in cli_help:
            if not cap.description and "description" in cli_help:
                cap.description = cli_help["description"]

            for arg in cli_help.get("positional_args", []):
                if arg not in cap.arguments:
                    cap.arguments[arg] = {
                        "type": "string",
                        "required": True,
                        "source": "cli-help",
                    }

            cap.metadata["cli_help_raw"] = cli_help.get("raw_help", "")

        return cap
