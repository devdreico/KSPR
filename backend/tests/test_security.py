import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from kspr_engine import main as main_module
from kspr_engine.auth import _resolve_secret_key
from kspr_engine.main import _is_safe_remote_url, _safe_stage_name, app
from kspr_engine.models import AnalysisRequest, SourceFile
from kspr_engine.sandbox import SafeSandbox, SandboxError


def test_safe_stage_name_strips_traversal():
    assert _safe_stage_name("report.pdf") == "report.pdf"
    assert _safe_stage_name("../../etc/passwd") == "passwd"
    assert _safe_stage_name("/absolute/path/file.txt") == "file.txt"
    assert _safe_stage_name("..\\..\\windows\\system32") == "system32"
    assert _safe_stage_name(None) == "upload.bin"
    assert _safe_stage_name("") == "upload.bin"
    assert _safe_stage_name("..") == "upload.bin"


def test_remote_url_guard_rejects_local_and_bad_schemes():
    assert _is_safe_remote_url("ftp://example.com/file") is False
    assert _is_safe_remote_url("file:///etc/passwd") is False
    assert _is_safe_remote_url("not-a-url") is False
    assert _is_safe_remote_url("http://127.0.0.1:8000/admin") is False
    assert _is_safe_remote_url("http://localhost:8000") is False
    assert _is_safe_remote_url("http://10.0.0.1/internal") is False
    assert _is_safe_remote_url("http://169.254.169.254/latest/meta-data") is False


def test_dangerous_endpoints_require_authentication():
    client = TestClient(app)
    assert client.post("/api/v1/decompilate").status_code == 401
    assert client.get("/api/v1/trees").status_code == 401


def test_resolve_secret_key_prefers_explicit_value(monkeypatch):
    monkeypatch.delenv("KSPR_JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert _resolve_secret_key("explicit-secret") == "explicit-secret"


def test_resolve_secret_key_uses_environment(monkeypatch):
    monkeypatch.setenv("KSPR_JWT_SECRET_KEY", "env-secret")
    assert _resolve_secret_key("") == "env-secret"


def test_sandbox_blocks_path_escape(tmp_path):
    sandbox = SafeSandbox(tmp_path)
    assert sandbox._validate_path("src/app.py") == (tmp_path / "src" / "app.py").resolve()
    with pytest.raises(SandboxError):
        sandbox._validate_path(f"../{tmp_path.name}-evil/pwn.txt")
    with pytest.raises(SandboxError):
        sandbox._validate_path("/etc/passwd")


def test_sandbox_writes_inside_workspace(tmp_path):
    sandbox = SafeSandbox(tmp_path)
    relative = sandbox.write_file("sub/new.txt", "hola")
    assert relative == "sub/new.txt"
    assert (tmp_path / "sub" / "new.txt").read_text(encoding="utf-8") == "hola"


def test_context_limit_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(main_module, "MAX_CONTEXT_BYTES", 10)
    request = AnalysisRequest(
        project_name="big",
        files=[SourceFile(path="a.py", content="0123456789abcdef")],
    )
    with pytest.raises(HTTPException) as exc:
        main_module._enforce_context_limit(request)
    assert exc.value.status_code == 413
