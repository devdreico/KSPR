"""Premium interactive shell layer for the KSPR CLI."""

from .app import ShellPrompt, shell_available
from .themes import DEFAULT_THEME, THEMES, Theme, get_theme

__all__ = ["DEFAULT_THEME", "THEMES", "ShellPrompt", "Theme", "get_theme", "shell_available"]
