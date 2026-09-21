from commands import COMMANDS, find_command, fuzzy_score, search_commands
from shell.themes import DEFAULT_THEME_NAME, THEMES, get_theme, theme_names


def test_registry_has_core_and_re_commands():
    names = {command.name for command in COMMANDS}
    for expected in {"help", "recon", "disasm", "decompile", "carve", "yara", "tools", "report", "theme"}:
        assert expected in names


def test_every_command_has_summary_and_category():
    for command in COMMANDS:
        assert command.summary
        assert command.category


def test_fuzzy_search_ranks_prefix_matches_first():
    results = [command.name for command in search_commands("c", limit=12)]
    assert "clear" in results
    assert "config" in results
    assert "carve" in results
    # "clear" starts with c, so it should appear before unrelated commands.
    assert results[0] in {"clear", "config", "connect", "compact", "context", "crypto", "cfg", "carve", "capa", "callgraph"}


def test_fuzzy_search_finds_decompile_by_subsequence():
    results = [command.name for command in search_commands("dcm", limit=5)]
    assert "decompile" in results


def test_fuzzy_score_prefers_exact_prefix():
    assert fuzzy_score("car", "carve") > fuzzy_score("car", "clear")
    assert fuzzy_score("zzz", "carve") == -1


def test_find_command_by_name_and_alias():
    assert find_command("/recon").name == "recon"
    assert find_command("dis").name == "disasm"
    assert find_command("nonexistent") is None


def test_themes_have_grayscale_default_and_variants():
    assert DEFAULT_THEME_NAME == "grayscale"
    names = theme_names()
    assert "grayscale" in names and "phosphor" in names
    assert get_theme("nope").name == "grayscale"
    assert set(THEMES) == set(names)


def test_completer_yields_commands_for_slash():
    from prompt_toolkit.document import Document
    from shell.completions import KSPRCompleter

    completer = KSPRCompleter()
    completions = list(completer.get_completions(Document("/car", 4), None))
    texts = [completion.text for completion in completions]
    assert any(text.startswith("/carve") for text in texts)
