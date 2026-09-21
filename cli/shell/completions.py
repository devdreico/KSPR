"""Fuzzy autocompletion for the KSPR shell.

Context prefixes:
  /  commands      @  workspace files      #  models
  %  agents        !  shell (passthrough)  :  symbols/offsets
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from commands import search_commands

try:  # prompt_toolkit is an optional-but-bundled dependency
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
except ImportError:  # pragma: no cover - exercised only without the extra
    Completer = object  # type: ignore[assignment,misc]

    class Completion:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            ...

    class Document:  # type: ignore[no-redef]
        ...


MAX_FILE_SUGGESTIONS = 200


def _meta_for(command, limit: int = 48) -> str:
    """Etiqueta enriquecida para el menú de autocompletado."""
    parts = [command.category]
    if command.aliases:
        parts.append("alias " + " ".join(f"/{alias}" for alias in command.aliases))
    if command.usage:
        parts.append(command.usage)
    if command.dangerous:
        parts.append("⚠ peligroso")
    text = " · ".join(parts)
    return text if len(text) <= limit else text[: limit - 1] + "…"


class KSPRCompleter(Completer):
    """Completer that dispatches on the leading character of the current token."""

    def __init__(
        self,
        workspace_provider: Callable[[], Path] | None = None,
        models_provider: Callable[[], Iterable[str]] | None = None,
        agents_provider: Callable[[], Iterable[str]] | None = None,
    ) -> None:
        self._workspace = workspace_provider
        self._models = models_provider
        self._agents = agents_provider

    def _current_token(self, document: Document) -> str:
        text = document.text_before_cursor
        if not text or text.endswith((" ", "\t", "\n")):
            return ""
        return text.split()[-1]

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        token = self._current_token(document)
        if token.startswith("/"):
            yield from self._complete_commands(token)
        elif token.startswith("@"):
            yield from self._complete_files(token)
        elif token.startswith("#"):
            yield from self._complete_values(token, self._models, "#")
        elif token.startswith("%"):
            yield from self._complete_values(token, self._agents, "%")

    def _complete_commands(self, token: str):
        query = token[1:]
        for command in search_commands(query, limit=40):
            yield Completion(
                f"/{command.name} ",
                start_position=-len(token),
                display=f"/{command.name}",
                display_meta=_meta_for(command),
            )

    def _complete_files(self, token: str):
        if not self._workspace:
            return
        query = token[1:].lower()
        try:
            root = Path(self._workspace()).resolve()
        except (OSError, TypeError):
            return
        count = 0
        for path in sorted(root.rglob("*")):
            if count >= MAX_FILE_SUGGESTIONS:
                break
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if any(part in {".git", "node_modules", ".venv", "__pycache__", "dist", "build"} for part in path.parts):
                continue
            if query and query not in relative.lower():
                continue
            count += 1
            yield Completion(
                f"@{relative} ",
                start_position=-len(token),
                display=f"@{relative}",
                display_meta="workspace",
            )

    @staticmethod
    def _complete_values(token: str, provider, prefix: str) -> Iterable[Completion]:
        if not provider:
            return
        query = token[1:].lower()
        try:
            values = list(provider())
        except Exception:
            return
        for value in values:
            if query and query not in str(value).lower():
                continue
            yield Completion(f"{prefix}{value} ", start_position=-len(token), display=f"{prefix}{value}")


class CommandPaletteCompleter(Completer):
    """Palette completer: search commands without requiring the leading slash."""

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        query = document.text_before_cursor.strip().lstrip("/")
        for command in search_commands(query, limit=60):
            yield Completion(
                f"/{command.name}",
                display=f"/{command.name}",
                display_meta=_meta_for(command, limit=64),
            )
