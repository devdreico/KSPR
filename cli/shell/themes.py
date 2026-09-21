"""Theme system for the KSPR shell.

Grayscale is the default identity; the exotic themes are opt-in accents used
by the rich renderer and the prompt toolkit style.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    primary: str          # títulos/acento principal
    secondary: str        # texto normal
    muted: str            # metadatos/bordes
    success: str
    warning: str
    error: str
    prompt: str           # color del prompt ❯
    completion: str       # color del menú de autocompletado
    completion_match: str


THEMES: dict[str, Theme] = {
    "grayscale": Theme(
        name="grayscale",
        label="Grayscale (identidad KSPR)",
        primary="#ffffff",
        secondary="#c8c8c8",
        muted="#6f6f6f",
        success="#e6e6e6",
        warning="#9a9a9a",
        error="#f2f2f2",
        prompt="#ffffff",
        completion="#9a9a9a",
        completion_match="#ffffff",
    ),
    "phosphor": Theme(
        name="phosphor",
        label="Phosphor CRT",
        primary="#7CFC9B",
        secondary="#3fae5c",
        muted="#1f5c31",
        success="#7CFC9B",
        warning="#d7ff7c",
        error="#ff7c7c",
        prompt="#7CFC9B",
        completion="#2f8f49",
        completion_match="#d7ffd7",
    ),
    "amber": Theme(
        name="amber",
        label="Amber Terminal",
        primary="#ffc46b",
        secondary="#c8943f",
        muted="#6b4d1f",
        success="#ffdf9e",
        warning="#ffc46b",
        error="#ff8a5c",
        prompt="#ffc46b",
        completion="#a5762f",
        completion_match="#fff0cf",
    ),
    "ice": Theme(
        name="ice",
        label="Ice Blue",
        primary="#9fd8ff",
        secondary="#5fa8d8",
        muted="#2f5a75",
        success="#b6f0ff",
        warning="#ffe08a",
        error="#ff9a9a",
        prompt="#9fd8ff",
        completion="#4f8fbf",
        completion_match="#e6f7ff",
    ),
    "void": Theme(
        name="void",
        label="Void Magenta",
        primary="#e0a6ff",
        secondary="#9a6fc0",
        muted="#4a2f63",
        success="#b6f0ff",
        warning="#ffd479",
        error="#ff7c9a",
        prompt="#e0a6ff",
        completion="#7a4fa0",
        completion_match="#f3e0ff",
    ),
}

DEFAULT_THEME = THEMES["grayscale"]
DEFAULT_THEME_NAME = "grayscale"


def get_theme(name: str | None) -> Theme:
    """Resolve a theme by name, falling back to grayscale."""
    return THEMES.get((name or "").strip().lower(), DEFAULT_THEME)


def theme_names() -> list[str]:
    return list(THEMES)
