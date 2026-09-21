"""Pure, dependency-free helpers for the KSPR CLI.

Everything in this module must be importable and testable without a terminal,
without network access and without the backend package. The interactive shell
(`kspr.py`) delegates here so its logic can be unit-tested in isolation.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

# Extensiones que KSPR puede leer de forma segura. Nunca se ejecutan.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".cs",
        ".java",
        ".kt",
        ".go",
        ".rb",
        ".php",
        ".rs",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".sql",
        ".html",
        ".htm",
        ".vue",
        ".svelte",
        ".css",
        ".scss",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".sh",
        ".env.example",
    }
)

# Directorios que nunca se recorren durante la ingesta.
SKIP_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "dist",
        "build",
        "target",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".idea",
        ".vscode",
        "coverage",
        ".next",
        ".nuxt",
    }
)

MAX_FILE_BYTES = 2_000_000


def extension_of(name: str) -> str:
    """Return the lowercase extension of a path name ('' when absent)."""
    clean = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    if clean.endswith(".env.example"):
        return ".env.example"
    return "." + clean.rsplit(".", 1)[-1].lower() if "." in clean else ""


def is_allowed_path(path: str) -> bool:
    """True when a path is relative, safe and has a supported extension."""
    normalized = (path or "").replace("\\", "/").strip()
    if not normalized or normalized.startswith("/") or ".." in normalized.split("/"):
        return False
    return extension_of(normalized) in ALLOWED_EXTENSIONS


def should_skip_dir(part: str) -> bool:
    return part in SKIP_DIRECTORIES


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token) safe for context budgeting."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def mask_secret(key: str | None) -> str:
    """Mask an API key for display without leaking it."""
    if not key:
        return "No configurada"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}…{key[-4:]} ({len(key)} chars)"


def safe_workspace_path(base: Path, relative: str) -> Path | None:
    """Resolve `relative` inside `base`, returning None on traversal attempts."""
    candidate = (base / relative).expanduser()
    try:
        resolved = candidate.resolve()
        base_resolved = base.resolve()
    except (OSError, RuntimeError):
        return None
    if resolved == base_resolved or base_resolved in resolved.parents:
        return resolved
    return None


def build_messages_prompt(messages: list[dict[str, Any]]) -> str:
    """Flatten a message list into a structured plain-text prompt."""
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", ""))
        content = message.get("content", "")
        if content:
            parts.append(f"[{role}]: {content}")
        for call in message.get("tool_calls") or []:
            fn = call.get("function", {})
            parts.append(f"[tool_call]: {fn.get('name', '')} {fn.get('arguments', '')}")
    return "\n".join(parts)


def expand_command_template(template: str, args_text: str) -> str:
    """Expand $ARGUMENTS and $1..$9 placeholders in a custom command template."""
    args = args_text.strip().split() if args_text.strip() else []
    result = (template or "").replace("$ARGUMENTS", args_text.strip())
    result = re.sub(r"\$(\d+)", lambda match: args[int(match.group(1)) - 1] if int(match.group(1)) <= len(args) else "", result)
    return result.strip()


def verify_license_code(code: str, paths: list[Path] | tuple[Path, ...]) -> bool:
    """Validate a license code against a list of candidate licenses.json files."""
    candidate = (code or "").strip()
    if not candidate:
        return False
    for path in paths:
        try:
            if not Path(path).is_file():
                continue
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        codes = data.get("codes", data)
        if isinstance(codes, dict) and candidate in codes:
            entry = codes[candidate]
            return not (isinstance(entry, dict) and entry.get("status", "active") != "active")
        if isinstance(codes, list) and candidate in codes:
            return True
    return False


def load_json_file(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning `default` on any failure."""
    try:
        if Path(path).is_file():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return default


def save_json_file(path: Path, data: Any) -> bool:
    """Persist JSON to disk atomically-ish; returns success."""
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def format_session_id(prefix: str = "%Y%m%d_%H%M%S") -> str:
    return time.strftime(prefix)


def truncate(text: str, limit: int, suffix: str = "...") -> str:
    if text is None:
        return ""
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: max(0, limit - len(suffix))] + suffix


def human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def parse_yes_no(value: str) -> bool | None:
    normalized = (value or "").strip().lower()
    if normalized in {"y", "yes", "s", "si", "sí", "1"}:
        return True
    if normalized in {"n", "no", "0"}:
        return False
    return None
