"""Motor de render visual de KSPR: tema, cajas, tablas, árboles, animaciones.

Diseñado con dos rutas equivalentes:
  * ``rich`` cuando está disponible y la salida es una TTY (máxima fidelidad).
  * ANSI 24-bit derivado del tema activo cuando no (funciona en cualquier
    terminal moderna, incluida la salida redirigida).

La identidad KSPR es escala de grises; los temas de acento son opt-in.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections.abc import Iterable, Sequence
from typing import Any

from shell.themes import DEFAULT_THEME_NAME, THEMES, get_theme

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    _RICH = True
except ImportError:  # pragma: no cover - rich es una dependencia declarada
    _RICH = False


class TerminalTheme:
    """Escala de grises ANSI para la UI profesional monocroma."""

    LIGHT_GRAY = "\033[37m"
    MID_GRAY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    INVERSE = "\033[7m"

    WHITE = "\033[97m"         # foco primario, títulos activos, prompt
    SILVER = "\033[37m"        # texto normal
    GRAPHITE = "\033[90m"      # bordes, divisores, metadatos
    CHARCOAL = "\033[2m"       # acentos tenues


# Wordmark ASCII oficial creado por el autor (diseño ░ de 6 líneas). Se
# conserva exactamente igual, incluida la sangría, para no alterar el diseño.
KSPR_ASCII: tuple[str, ...] = (
    "░                             ",
    " ░░░░░░░░░░                              ",
    "░░░░░░░░░░   ░░  ░░ ░░░░░░ ░░░░░░  ░░░░░ ",
    "░   ░░   ░   ░░ ░░  ░░░░░  ░░   ░ ░░   ░░",
    "░░░░░░░░░░   ░░░░     ░░░░ ░░░░░░ ░░░░░░ ",
    "░░░░  ░░░░   ░░ ░░░ ░░░░░░ ░░░    ░░   ░░",
)

KSPR_SUBTITLE = "KSPR AI · Empresarial  |  KSPR I ENGINE"
KSPR_TAGLINE = "Static analysis · Evidence-first · Context Trees"

# Animaciones y glifos de estado.
_SPINNER_FRAMES: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_SCAN_FRAMES: tuple[str, ...] = ("░", "▒", "▓", "█")
_SPARK_BLOCKS: tuple[str, ...] = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
_STATUS_ICONS = {"ok": "✓", "err": "✕", "warn": "!", "info": "›", "dot": "●"}
_STATUS_ROLE = {"ok": "success", "err": "error", "warn": "warning", "info": "secondary", "dot": "primary"}


def _rich_enabled() -> bool:
    try:
        return _RICH and sys.stdout.isatty()
    except (ValueError, AttributeError):
        return False


_console: Console | None = None


def _get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(highlight=False, soft_wrap=True)
    return _console


def _hex_to_ansi(value: str) -> str:
    """Convierte '#rrggbb' a un escape ANSI truecolor (con fallback seguro)."""
    raw = (value or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    try:
        red, green, blue = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return TerminalTheme.SILVER
    return f"\033[38;2;{red};{green};{blue}m"


_ANSI_CACHE: dict[str, dict[str, str]] = {}


def _theme_ansi(theme) -> dict[str, str]:
    cached = _ANSI_CACHE.get(theme.name)
    if cached is not None:
        return cached
    mapping = {
        role: _hex_to_ansi(getattr(theme, role))
        for role in ("primary", "secondary", "muted", "success", "warning", "error", "prompt", "completion", "completion_match")
    }
    _ANSI_CACHE[theme.name] = mapping
    return mapping


class TerminalUI:
    theme_name: str = DEFAULT_THEME_NAME
    animations_enabled: bool = True

    # ---- tema / configuración -------------------------------------------
    @classmethod
    def set_theme(cls, name: str) -> str:
        """Cambia el tema activo; devuelve el nombre aplicado."""
        theme = get_theme(name)
        cls.theme_name = theme.name
        return theme.name

    @classmethod
    def set_animations(cls, enabled: bool) -> None:
        cls.animations_enabled = bool(enabled)

    @classmethod
    def animations(cls) -> bool:
        return cls.animations_enabled

    @classmethod
    def _theme(cls):
        return get_theme(cls.theme_name)

    @classmethod
    def _c(cls, role: str) -> str:
        """Color ANSI del rol semántico del tema activo."""
        return _theme_ansi(cls._theme()).get(role, TerminalTheme.SILVER)

    @classmethod
    def _animate(cls) -> bool:
        """True cuando se puede dibujar animación (flag + TTY)."""
        try:
            tty = sys.stdout.isatty()
        except (ValueError, AttributeError):
            tty = False
        return bool(cls.animations_enabled and tty)

    @classmethod
    def render_mode(cls) -> str:
        """Describe el backend de render activo para diagnóstico."""
        if _rich_enabled():
            return "rich"
        return "ANSI 24-bit" if _RICH else "ANSI plano"

    # ---- primitivas base ------------------------------------------------
    @staticmethod
    def print_colored(text: str, color: str = TerminalTheme.SILVER, bold: bool = False) -> None:
        prefix = TerminalTheme.BOLD if bold else ""
        print(f"{color}{prefix}{text}{TerminalTheme.RESET}")

    @staticmethod
    def get_width() -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    @classmethod
    def status_line(cls, kind: str, text: str) -> None:
        """Línea de estado semántica: ok / err / warn / info / dot."""
        icon = _STATUS_ICONS.get(kind, "›")
        role = _STATUS_ROLE.get(kind, "secondary")
        cls.print_colored(f"{icon} {text}", cls._c(role))

    # ---- cabecera --------------------------------------------------------
    @classmethod
    def print_header(cls, subtitle: str = "") -> None:
        """Renderiza el wordmark oficial KSPR con el tema activo."""
        label = f"{KSPR_SUBTITLE}  |  {subtitle}" if subtitle else KSPR_SUBTITLE
        if _rich_enabled():
            console = _get_console()
            console.print()
            for line in KSPR_ASCII:
                console.print(line, style=f"{cls._theme().primary} bold")
            console.print(label, style=cls._theme().muted)
            console.print(KSPR_TAGLINE, style=cls._theme().muted)
            console.print()
            return
        print()
        for line in KSPR_ASCII:
            cls.print_colored(line, TerminalTheme.WHITE, bold=True)
        cls.print_colored(label, TerminalTheme.GRAPHITE)
        cls.print_colored(KSPR_TAGLINE, TerminalTheme.MID_GRAY)
        print()

    # ---- nuevos componentes visuales ------------------------------------
    @classmethod
    def print_divider(cls, label: str = "") -> None:
        width = min(cls.get_width() - 2, 86)
        if label:
            text = f" {label} "
            side = max(0, width - len(text) - 2)
            left = "─" * (side // 2)
            right = "─" * (side - side // 2)
            if _rich_enabled():
                _get_console().print(f"{left}{text}{right}", style=cls._theme().muted)
                return
            cls.print_colored(left, TerminalTheme.GRAPHITE)
            cls.print_colored(text, cls._c("primary"), bold=True)
            cls.print_colored(right, TerminalTheme.GRAPHITE)
            return
        line = "─" * width
        if _rich_enabled():
            _get_console().print(line, style=cls._theme().muted)
            return
        cls.print_colored(line, TerminalTheme.GRAPHITE)

    @classmethod
    def print_kv(cls, pairs: Sequence[tuple[str, Any]], title: str = "") -> None:
        pairs = [(str(key), str(value)) for key, value in pairs]
        if not pairs:
            return
        width = max(len(key) for key, _ in pairs)
        if _rich_enabled():
            console = _get_console()
            if title:
                console.print(title, style=f"{cls._theme().primary} bold")
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style=cls._theme().muted, justify="right")
            grid.add_column(style=cls._theme().secondary)
            for key, value in pairs:
                grid.add_row(key, value)
            console.print(grid)
            return
        if title:
            cls.print_colored(title, cls._c("primary"), bold=True)
        for key, value in pairs:
            print(f"{cls._c('muted')}{key.rjust(width)}{TerminalTheme.RESET}  {cls._c('secondary')}{value}{TerminalTheme.RESET}")

    @classmethod
    def print_status(cls, entries: Sequence[tuple[str, str, str]]) -> None:
        """entries: (etiqueta, estado ok|err|warn|info|dot, detalle)."""
        for label, state, detail in entries:
            icon = _STATUS_ICONS.get(state, "›")
            color = cls._c(_STATUS_ROLE.get(state, "secondary"))
            tail = f"  {TerminalTheme.GRAPHITE}{detail}{TerminalTheme.RESET}" if detail else ""
            print(f"  {color}{icon}{TerminalTheme.RESET} {cls._c('secondary')}{label}{TerminalTheme.RESET}{tail}")

    @classmethod
    def print_badges(cls, items: Iterable[str], label: str = "") -> None:
        parts = [f"{cls._c('primary')}▐{TerminalTheme.RESET} {item} {cls._c('primary')}▌{TerminalTheme.RESET}" for item in items]
        if not parts:
            return
        prefix = f"{cls._c('muted')}{label}  {TerminalTheme.RESET}" if label else ""
        print(prefix + "  ".join(parts))

    @classmethod
    def print_bar(cls, label: str, value: float, total: float, width: int = 26) -> None:
        pct = 0 if total <= 0 else max(0, min(100, int(value / total * 100)))
        filled = int(pct / 100 * width)
        bar = "█" * filled + "░" * max(0, width - filled)
        print(
            f"{cls._c('muted')}{label.ljust(12)}{TerminalTheme.RESET}"
            f"[{cls._c('primary')}{bar}{TerminalTheme.RESET}] "
            f"{cls._c('secondary')}{pct:>3}%{TerminalTheme.RESET}"
        )

    @classmethod
    def print_sparkline(cls, values: Sequence[float], label: str = "") -> None:
        if not values:
            return
        low, high = min(values), max(values)
        span = (high - low) or 1.0
        spark = "".join(_SPARK_BLOCKS[min(len(_SPARK_BLOCKS) - 1, int((value - low) / span * (len(_SPARK_BLOCKS) - 1)))] for value in values)
        prefix = f"{cls._c('muted')}{label.ljust(12)}{TerminalTheme.RESET}" if label else ""
        print(f"{prefix}{cls._c('primary')}{spark}{TerminalTheme.RESET}  {cls._c('muted')}min {low:.0f} · max {high:.0f}{TerminalTheme.RESET}")

    @classmethod
    def print_command_grid(cls, commands: Sequence[Any], columns: int = 3) -> None:
        """Mapa de comandos agrupados por categoría en columnas compactas."""
        groups: dict[str, list[Any]] = {}
        for command in commands:
            groups.setdefault(getattr(command, "category", "core"), []).append(command)

        if _rich_enabled():
            console = _get_console()
            for category, items in groups.items():
                console.print(f"[{category}]", style=f"{cls._theme().primary} bold")
                grid = Table.grid(padding=(0, 3))
                for _ in range(min(columns, max(1, len(items)))):
                    grid.add_column(style=cls._theme().secondary, no_wrap=True)
                row: list[str] = []
                for command in items:
                    row.append(f"/{command.name}")
                    if len(row) == columns:
                        grid.add_row(*row)
                        row = []
                if row:
                    row.extend([""] * (columns - len(row)))
                    grid.add_row(*row)
                console.print(grid)
            return

        for category, items in groups.items():
            cls.print_colored(f"[{category}]", cls._c("primary"), bold=True)
            names = [f"/{command.name}" for command in items]
            column_width = max(len(name) for name in names) + 2
            for index in range(0, len(names), columns):
                chunk = names[index:index + columns]
                print("  " + "".join(name.ljust(column_width) for name in chunk).rstrip())

    @classmethod
    def print_theme_swatches(cls) -> None:
        for theme in THEMES.values():
            marker = "●" if theme.name == cls.theme_name else "○"
            if _rich_enabled():
                text = Text()
                text.append(f"  {marker} ", style=theme.primary)
                text.append(f"{theme.name.ljust(12)}", style=theme.primary)
                text.append(theme.label, style=theme.secondary)
                text.append("   ", style=theme.muted)
                text.append("████", style=theme.primary)
                text.append("████", style=theme.secondary)
                text.append("████", style=theme.muted)
                _get_console().print(text)
                continue
            colors = _theme_ansi(theme)
            print(
                f"  {colors['primary']}{marker} {theme.name.ljust(12)}{colors['secondary']}{theme.label}"
                f"   {colors['primary']}████{colors['secondary']}████{colors['muted']}████{TerminalTheme.RESET}"
            )

    # ---- rich: cajas, tablas y árboles ----------------------------------
    @classmethod
    def print_box(cls, title: str, lines: Sequence[Any]) -> None:
        if _rich_enabled():
            body = Text("\n".join(str(line) for line in lines))
            _get_console().print(Panel(body, title=title, border_style=cls._theme().primary, title_align="left"))
            return
        width = min(max(len(title) + 6, max((len(str(line)) for line in lines), default=40) + 4), cls.get_width() - 2)
        horizontal = "─" * (width - 2)
        print()
        cls.print_colored(f"┌─ {title} " + "─" * max(0, width - len(title) - 4) + "┐", TerminalTheme.WHITE, bold=True)
        for line in lines:
            text = str(line)
            padding = max(0, width - len(text) - 4)
            cls.print_colored(f"│  {text}" + " " * padding + "│", TerminalTheme.SILVER)
        cls.print_colored(f"└{horizontal}┘", TerminalTheme.GRAPHITE)
        print()

    @classmethod
    def print_table(cls, title: str, columns: Sequence[str], rows: Sequence[Sequence[Any]], max_rows: int = 60) -> None:
        """Renderiza una tabla; rich si está disponible, caja ASCII si no."""
        visible = list(rows[:max_rows])
        if _rich_enabled():
            table = Table(title=title, border_style=cls._theme().muted, header_style=cls._theme().primary, title_justify="left")
            for column in columns:
                table.add_column(str(column), overflow="fold")
            for row in visible:
                table.add_row(*[str(cell) for cell in row])
            _get_console().print(table)
            if len(rows) > max_rows:
                cls.print_colored(f"  … {len(rows) - max_rows} filas omitidas", TerminalTheme.GRAPHITE)
            return
        if not visible:
            cls.print_box(title, ["(sin datos)"])
            return
        widths = [
            max(len(str(columns[i])), *(len(str(row[i])) for row in visible))
            for i in range(len(columns))
        ]
        header = " | ".join(str(columns[i]).ljust(widths[i]) for i in range(len(columns)))
        body = [
            " | ".join(str(row[i]).ljust(widths[i]) for i in range(len(columns)))
            for row in visible
        ]
        cls.print_box(title, [header, "-" * len(header), *body])

    @classmethod
    def print_tree(cls, title: str, root_label: str, children: Sequence[tuple[str, Sequence[str]]]) -> None:
        """Renderiza un árbol de dos niveles (raíz -> grupos -> elementos)."""
        if _rich_enabled():
            tree = Tree(f"[bold]{root_label}[/bold]")
            for group, items in children:
                node = tree.add(group)
                for item in items:
                    node.add(str(item))
            _get_console().print(Panel(tree, title=title, border_style=cls._theme().muted, title_align="left"))
            return
        lines = [root_label]
        for group, items in children:
            lines.append(f"├─ {group}")
            lines.extend(f"│  ├─ {item}" for item in items)
        cls.print_box(title, lines)

    @classmethod
    def print_route_tree(cls, title: str, root_label: str, groups: Sequence[tuple[str, Sequence[str]]]) -> None:
        """Árbol de rutas backend ↔ comando CLI."""
        cls.print_tree(title, root_label, groups)

    # ---- dashboard de sesión --------------------------------------------
    @classmethod
    def print_session_banner(cls, *args: Any, **kwargs: Any) -> None:
        # Soporta 6 o 7 argumentos posicionales y también kwargs.
        if len(args) == 6:
            session_id = time.strftime("%Y%m%d_%H%M%S")
            provider, model, workspace, attached_count, tokens_used, max_tokens = args
        elif len(args) == 7:
            session_id, provider, model, workspace, attached_count, tokens_used, max_tokens = args
        else:
            session_id = kwargs.get("session_id", time.strftime("%Y%m%d_%H%M%S"))
            provider = kwargs.get("provider", "gemini")
            model = kwargs.get("model", "gemini-2.5-flash")
            workspace = kwargs.get("workspace", os.getcwd())
            attached_count = kwargs.get("attached_count", 0)
            tokens_used = kwargs.get("tokens_used", 1250)
            max_tokens = kwargs.get("max_tokens", 128000)

        theme = cls._theme()
        pct = int((tokens_used / max_tokens) * 100) if max_tokens > 0 else 0
        pct = max(0, min(100, pct))
        bar_width = 14
        filled = int(pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        ws_str = str(workspace)
        if len(ws_str) > 34:
            ws_str = "…" + ws_str[-33:]

        title = f"KSPR I · {provider}:{model}"
        if _rich_enabled():
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style=theme.muted)
            grid.add_column(style=theme.secondary)
            grid.add_row("sesión", str(session_id))
            grid.add_row("ctx", f"[{bar}] {tokens_used // 1000}k/{max_tokens // 1000}k ({pct}%)")
            grid.add_row("workspace", f"{ws_str}   ·   adjuntos: {attached_count}")
            grid.add_row("tips", "[@] adjuntar   [/] comandos   [Ctrl+K] paleta   [Ctrl+C] salir")
            _get_console().print(Panel(grid, title=title, border_style=theme.muted, title_align="left"))
            return

        width = min(cls.get_width() - 2, 90)
        header = f"┌─ {title}"
        dash = max(0, width - len(header) - 1)
        cls.print_colored(header + " " + "─" * dash + "┐", theme.muted, bold=True)
        rows = [
            f"│  sesión: {session_id}",
            f"│  ctx: [{bar}] {tokens_used // 1000}k/{max_tokens // 1000}k ({pct}%)",
            f"│  dir: {ws_str}   ·   files: {attached_count}",
            "│  tips: [@] attach   [/] cmds   [^K] palette   [^C] exit",
        ]
        for row in rows:
            padding = max(0, width - len(row) - 1)
            cls.print_colored(row + " " * padding + "│", theme.secondary)
        cls.print_colored("└" + "─" * (width - 2) + "┘", theme.muted)

    # ---- animaciones -----------------------------------------------------
    @classmethod
    async def animate_spinner(cls, task_coro, message: str) -> tuple[Any, float]:
        """Ejecuta ``task_coro`` mostrando un spinner; devuelve (resultado, segundos)."""
        task = asyncio.create_task(task_coro)
        start_time = time.time()
        draw = cls._animate()
        idx = 0

        if draw:
            sys.stdout.write("\033[?25l")
        try:
            while not task.done():
                if draw:
                    elapsed = time.time() - start_time
                    frame = _SPINNER_FRAMES[idx % len(_SPINNER_FRAMES)]
                    sys.stdout.write(f"\r{cls._c('primary')}{frame} {message} {TerminalTheme.GRAPHITE}[ {elapsed:.1f}s ]{TerminalTheme.RESET}")
                    sys.stdout.flush()
                    idx += 1
                await asyncio.sleep(0.08)
            if draw:
                sys.stdout.write("\r\033[K")
            elapsed = time.time() - start_time
            try:
                result = await task
            except Exception:
                if draw:
                    sys.stdout.write(f"{cls._c('error')}{_STATUS_ICONS['err']} {message} {TerminalTheme.GRAPHITE}[ {elapsed:.1f}s ]{TerminalTheme.RESET}\n")
                    sys.stdout.flush()
                raise
            if draw:
                sys.stdout.write(f"{cls._c('success')}{_STATUS_ICONS['ok']} {message} {TerminalTheme.GRAPHITE}[ {elapsed:.1f}s ]{TerminalTheme.RESET}\n")
                sys.stdout.flush()
            return result, elapsed
        finally:
            if draw:
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()

    @classmethod
    def animate_typewriter(cls, text: str, delay: float = 0.008, role: str = "secondary") -> None:
        """Escribe un texto carácter a carácter (instantáneo si no hay TTY)."""
        if not cls._animate():
            cls.print_colored(text, cls._c(role))
            return
        color = cls._c(role)
        sys.stdout.write(color)
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write(TerminalTheme.RESET + "\n")
        sys.stdout.flush()

    @classmethod
    def animate_scan(cls, message: str, duration: float = 1.2, width: int = 26) -> None:
        """Barra de escaneo de una pasada (visual de progreso determinista)."""
        if not cls._animate():
            cls.status_line("ok", message)
            return
        steps = max(1, int(duration / 0.04))
        sys.stdout.write("\033[?25l")
        try:
            for step in range(steps + 1):
                progress = step / steps
                filled = int(progress * width)
                bar = "".join(_SCAN_FRAMES[min(len(_SCAN_FRAMES) - 1, int(progress * 4))] for _ in range(filled))
                bar += "░" * (width - filled)
                sys.stdout.write(f"\r{cls._c('primary')}▕{bar}▏{TerminalTheme.RESET} {cls._c('secondary')}{message}{TerminalTheme.RESET}")
                sys.stdout.flush()
                time.sleep(0.04)
            sys.stdout.write(f"\r\033[K{cls._c('success')}{_STATUS_ICONS['ok']}{TerminalTheme.RESET} {message}\n")
            sys.stdout.flush()
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    # ---- pasos de herramienta y respuestas -------------------------------
    @classmethod
    def print_tool_step(cls, fn_name: str, args: dict, result: str, duration_ms: float) -> None:
        args_str = json.dumps(args, ensure_ascii=False)
        if len(args_str) > 60:
            args_str = args_str[:57] + "..."
        trunc_res = str(result).replace("\n", " ").strip()
        if len(trunc_res) > 80:
            trunc_res = trunc_res[:77] + "..."

        cls.print_colored(f"  ● Tool Call: {fn_name}", cls._c("primary"), bold=True)
        cls.print_colored(f"    ├─ args: {args_str}", cls._c("muted"))
        cls.print_colored(f"    └─ result: {_STATUS_ICONS['ok']} · {duration_ms:.0f}ms · {trunc_res}", cls._c("secondary"))

    @classmethod
    def print_response(cls, title: str, text: str | Sequence[str], latency: float = 0.0) -> None:
        if isinstance(text, (list, tuple)):
            lines = [str(line) for line in text]
            raw = "\n".join(lines)
        else:
            raw = str(text)
            lines = raw.splitlines() or [raw]
        lat_str = f" │ {latency:.2f}s " if latency > 0 else ""

        if _rich_enabled():
            try:
                body: Any = Markdown(raw)
            except Exception:
                body = Text(raw)
            _get_console().print(Panel(body, title=f"{title}{lat_str}", border_style=cls._theme().primary, title_align="left"))
            return

        width = min(max(len(title) + 16, max((len(line) for line in lines), default=40) + 4), cls.get_width() - 2)
        horizontal = "─" * (width - 2)
        print()
        cls.print_colored(f"┌── {title}{lat_str}" + "─" * max(0, width - len(title) - len(lat_str) - 3) + "┐", TerminalTheme.WHITE, bold=True)
        for line in lines:
            while len(line) > width - 4:
                chunk = line[:width - 4]
                line = line[width - 4:]
                cls.print_colored(f"│  {chunk}  │", TerminalTheme.SILVER)
            padding = max(0, width - len(line) - 4)
            cls.print_colored(f"│  {line}" + " " * padding + "│", TerminalTheme.SILVER)
        cls.print_colored(f"└{horizontal}┘", TerminalTheme.WHITE)
        print()
