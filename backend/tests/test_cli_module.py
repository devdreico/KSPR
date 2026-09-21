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
