import json

import kspr


def test_export_session_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(kspr, "CONFIG_DIR", tmp_path)
    history = [{"role": "user", "content": "hola"}, {"role": "assistant", "content": "hey"}]
    target = kspr.export_session(history, "sess1", "md")
    assert target.name == "sess1.md"
    text = target.read_text(encoding="utf-8")
    assert "## Usuario" in text
    assert "## KSPR I" in text
    assert "hola" in text and "hey" in text


def test_export_session_json(tmp_path, monkeypatch):
    monkeypatch.setattr(kspr, "CONFIG_DIR", tmp_path)
    history = [{"role": "user", "content": "dato"}]
    target = kspr.export_session(history, "sess2", "json")
    assert json.loads(target.read_text(encoding="utf-8")) == history


def test_doctor_report_contains_key_sections(tmp_path):
    lines = kspr.doctor_report({}, "local", "kspr-local", tmp_path)
    joined = "\n".join(lines)
    assert "KSPR CLI" in joined
    assert "Dependencias" in joined
    assert "Proveedor activo: local" in joined


def test_kspr_ascii_wordmark_is_indexed_and_aligned(capsys):
    from kspr_terminal_ui import KSPR_ASCII, KSPR_SUBTITLE

    assert len(KSPR_ASCII) == 5
    widths = {len(line) for line in KSPR_ASCII}
    assert len(widths) == 1, f"las líneas del wordmark deben medir igual: {widths}"
    assert all(set(line) <= {"░", " "} for line in KSPR_ASCII)
    assert "KSPR" in KSPR_SUBTITLE

    kspr.print_header("test")
    output = capsys.readouterr().out
    assert KSPR_ASCII[0] in output
    assert KSPR_SUBTITLE in output
