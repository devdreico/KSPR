"""Tests for the KSPR visual engine and the new visual/interconnect commands."""

import asyncio

import kspr
from commands import find_command, search_commands
from kspr_terminal_ui import TerminalTheme, TerminalUI


def test_ansi_constants_have_escape_sequences():
    # Regresión: LIGHT_GRAY/MID_GRAY perdían el \033 y se imprimían literales.
    assert TerminalTheme.LIGHT_GRAY.startswith("\033[")
    assert TerminalTheme.MID_GRAY.startswith("\033[")


def test_visual_primitives_render(capsys):
    TerminalUI.set_theme("grayscale")
    TerminalUI.set_animations(False)
    TerminalUI.print_divider("SECCIÓN")
    TerminalUI.print_kv([("clave", "valor")], title="KV")
    TerminalUI.print_status([("ok", "ok", "detalle"), ("warn", "warn", ""), ("err", "err", ""), ("dot", "dot", "")])
    TerminalUI.print_badges(["uno", "dos"], label="badges")
    TerminalUI.print_bar("contexto", 5, 10)
    TerminalUI.print_sparkline([1, 3, 2, 8, 5], "actividad")
    TerminalUI.print_command_grid([find_command("recon")])
    TerminalUI.print_theme_swatches()
    output = capsys.readouterr().out
    assert "SECCIÓN" in output
    assert "valor" in output
    assert "contexto" in output
    assert "actividad" in output
    assert "grayscale" in output


def test_animate_primitives_degrade_without_tty(capsys):
    TerminalUI.set_animations(True)  # capsys no es TTY => se degrada sin animar
    TerminalUI.animate_typewriter("hola mundo")
    TerminalUI.animate_scan("escaneo", duration=0.01)
    output = capsys.readouterr().out
    assert "hola mundo" in output
    assert "escaneo" in output


def test_spinner_returns_result_and_elapsed():
    async def work():
        await asyncio.sleep(0)
        return 7

    result, elapsed = asyncio.run(TerminalUI.animate_spinner(work(), "spinner"))
    assert result == 7
    assert elapsed >= 0


def test_render_mode_reports_backend():
    assert TerminalUI.render_mode() in {"rich", "ANSI 24-bit", "ANSI plano"}


def test_new_commands_resolve_with_aliases():
    assert find_command("/palette").name == "palette"
    assert find_command("cmds").name == "palette"
    assert find_command("stats").name == "status"
    assert find_command("ui").name == "visual"
    assert find_command("api-map").name == "routes"
    assert find_command("/routes").name == "routes"


def test_command_map_search_finds_new_commands():
    names = {command.name for command in search_commands("mapa", limit=8)}
    assert "map" in names


def test_route_cli_hint_maps_known_paths():
    assert kspr.route_cli_hint("/api/v1/decompilate") == "/decompilate"
    assert kspr.route_cli_hint("/api/v1/trees") == "/trees"
    assert kspr.route_cli_hint("/api/v1/re/analyze") == "/recon"
    assert kspr.route_cli_hint("/api/v1/desconocido") == "—"
