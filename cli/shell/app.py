"""prompt_toolkit application wrapper for the KSPR shell.

Provides fuzzy completion, a Ctrl+K command palette, a live bottom toolbar and
persistent history. Degrades gracefully when prompt_toolkit is unavailable or
the session is not attached to a TTY (the CLI keeps its readline fallback).
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from pathlib import Path

from .completions import CommandPaletteCompleter, KSPRCompleter
from .themes import Theme, get_theme

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import run_in_terminal
    from prompt_toolkit.history import FileHistory, InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style

    _PTK = True
except ImportError:  # pragma: no cover
    _PTK = False


def shell_available() -> bool:
    """True when the premium shell can run (prompt_toolkit + TTY)."""
    if not _PTK:
        return False
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except (ValueError, AttributeError):
        return False


class ShellPrompt:
    """Thin, testable wrapper around a configured PromptSession."""

    def __init__(
        self,
        theme: Theme | str | None = None,
        status_provider: Callable[[], str] | None = None,
        workspace_provider: Callable[[], Path] | None = None,
        models_provider: Callable[[], Iterable[str]] | None = None,
        agents_provider: Callable[[], Iterable[str]] | None = None,
        help_callback: Callable[[], None] | None = None,
        history_path: Path | None = None,
    ) -> None:
        if not _PTK:
            raise RuntimeError("prompt_toolkit no está instalado")
        self.theme = theme if isinstance(theme, Theme) else get_theme(str(theme) if theme else None)
        self._status_provider = status_provider
        self._help_callback = help_callback
        self.completer = KSPRCompleter(
            workspace_provider=workspace_provider,
            models_provider=models_provider,
            agents_provider=agents_provider,
        )
        if history_path is not None:
            try:
                history_path.parent.mkdir(parents=True, exist_ok=True)
                self._history = FileHistory(str(history_path))
            except OSError:
                self._history = InMemoryHistory()
        else:
            self._history = InMemoryHistory()

        self._bindings = self._build_bindings()
        self._style = self._build_style(self.theme)
        self.session = PromptSession(
            completer=self.completer,
            complete_while_typing=True,
            key_bindings=self._bindings,
            history=self._history,
            bottom_toolbar=self._toolbar,
            style=self._style,
            enable_history_search=False,
        )

    # ---- internals ----
    def _toolbar(self) -> str:
        if not self._status_provider:
            return ""
        try:
            return self._status_provider()
        except Exception:
            return ""

    def _build_style(self, theme: Theme) -> Style:
        return Style.from_dict(
            {
                "prompt": f"{theme.prompt} bold",
                "completion-menu.completion": f"bg:#000000 {theme.secondary}",
                "completion-menu.completion.current": f"bg:{theme.completion_match} #000000 bold",
                "completion-menu.meta.completion": f"bg:#000000 {theme.muted}",
                "completion-menu.meta.completion.current": f"bg:{theme.completion_match} #000000",
                "bottom-toolbar": f"bg:#000000 {theme.muted}",
                "bottom-toolbar.text": f"bg:#000000 {theme.muted}",
            }
        )

    def _build_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("c-k")
        async def _palette(event) -> None:
            def run() -> str | None:
                return self.run_palette()

            selected = await run_in_terminal(run)
            if selected:
                event.current_buffer.text = selected
                event.current_buffer.cursor_position = len(selected)

        @bindings.add("f1")
        def _help(event) -> None:
            event.current_buffer.text = "/help"
            event.current_buffer.cursor_position = len(event.current_buffer.text)
            event.current_buffer.validate_and_handle()

        return bindings

    # ---- public API ----
    def prompt(self, message: str = "❯ ") -> str:
        return self.session.prompt(message)

    def run_palette(self) -> str | None:
        """Search all commands in a nested prompt and return the chosen one."""
        palette = PromptSession(
            completer=CommandPaletteCompleter(),
            complete_while_typing=True,
            history=InMemoryHistory(),
            style=self._style,
            bottom_toolbar="Paleta · escribe para filtrar · Enter selecciona · Ctrl+C cancela",
        )
        try:
            return palette.prompt("⌘ ") or None
        except (KeyboardInterrupt, EOFError):
            return None
