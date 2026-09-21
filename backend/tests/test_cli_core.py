import json
from pathlib import Path

import kspr_core as core


def test_extension_and_allowed_paths():
    assert core.extension_of("src/Main.PY") == ".py"
    assert core.extension_of("Dockerfile") == ""
    assert core.is_allowed_path("src/app.tsx") is True
    assert core.is_allowed_path("./src/app.tsx") is True
    assert core.is_allowed_path("../secret.py") is False
    assert core.is_allowed_path("/etc/passwd") is False
    assert core.is_allowed_path("binary.exe") is False
    assert core.is_allowed_path("") is False


def test_skip_directory_rules():
    assert core.should_skip_dir(".git") is True
    assert core.should_skip_dir("node_modules") is True
    assert core.should_skip_dir("src") is False


def test_estimate_tokens_scales_with_length():
    assert core.estimate_tokens("") == 0
    assert core.estimate_tokens("a" * 400) == 100
    assert core.estimate_tokens("hola") >= 1


def test_mask_secret_never_reveals_full_key():
    assert core.mask_secret(None) == "No configurada"
    assert core.mask_secret("short") == "*****"
    key = "sk-1234567890abcdef"
    masked = core.mask_secret(key)
    assert key not in masked
    assert masked.startswith("sk-1")
    assert masked.endswith(f"cdef ({len(key)} chars)")


def test_safe_workspace_path_blocks_traversal(tmp_path: Path):
    inside = core.safe_workspace_path(tmp_path, "src/app.py")
    assert inside == (tmp_path / "src" / "app.py")
    assert core.safe_workspace_path(tmp_path, "../escape.py") is None
    assert core.safe_workspace_path(tmp_path, "/etc/passwd") is None


def test_build_messages_prompt_includes_tool_calls():
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": None, "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "a.py"}}}]},
        {"role": "tool", "content": "contenido", "tool_call_id": "1"},
    ]
    prompt = core.build_messages_prompt(messages)
    assert "[user]: hola" in prompt
    assert "read_file" in prompt
    assert "[tool]: contenido" in prompt


def test_expand_command_template():
    assert core.expand_command_template("Analiza $ARGUMENTS", "src/app.py") == "Analiza src/app.py"
    assert core.expand_command_template("Hola $1 y $2", "A B") == "Hola A y B"
    assert core.expand_command_template("Solo $1", "") == "Solo"


def test_verify_license_code_reads_file(tmp_path: Path):
    license_file = tmp_path / "licenses.json"
    license_file.write_text(
        json.dumps({"codes": {"KSPR-OK": {"status": "active"}, "KSPR-OLD": {"status": "revoked"}}}),
        encoding="utf-8",
    )
    assert core.verify_license_code("KSPR-OK", [license_file]) is True
    assert core.verify_license_code("KSPR-OLD", [license_file]) is False
    assert core.verify_license_code("KSPR-MISSING", [license_file]) is False
    assert core.verify_license_code("", [license_file]) is False
    assert core.verify_license_code("KSPR-OK", [tmp_path / "nope.json"]) is False


def test_load_and_save_json_roundtrip(tmp_path: Path):
    target = tmp_path / "nested" / "data.json"
    assert core.save_json_file(target, {"a": 1}) is True
    assert core.load_json_file(target, {}) == {"a": 1}
    assert core.load_json_file(tmp_path / "absent.json", {"default": True}) == {"default": True}


def test_truncate_and_human_bytes():
    assert core.truncate("abcdef", 4) == "a..."
    assert core.truncate("abc", 10) == "abc"
    assert core.human_bytes(512) == "512 B"
    assert core.human_bytes(2048) == "2.0 KB"


def test_parse_yes_no():
    assert core.parse_yes_no("y") is True
    assert core.parse_yes_no("No") is False
    assert core.parse_yes_no("maybe") is None
