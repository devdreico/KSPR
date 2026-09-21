import io
import zipfile

from fastapi.testclient import TestClient
from kspr_engine.main import app


def _auth_headers(username: str = "reuser", email: str = "re@example.com") -> dict[str, str]:
    client = TestClient(app)
    response = client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": "password123"})
    if response.status_code == 409:
        response = client.post("/api/v1/auth/login", json={"identifier": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        handle.writestr("src/app.py", "print('hola')")
    return buffer.getvalue()


def test_re_tools_endpoint_lists_tools():
    client = TestClient(app)
    response = client.get("/api/v1/re/tools")
    assert response.status_code == 200
    payload = response.json()
    assert "installed" in payload and "missing" in payload


def test_re_analyze_requires_auth():
    client = TestClient(app)
    response = client.post("/api/v1/re/analyze", files={"file": ("ctx.zip", _zip_bytes(), "application/zip")})
    assert response.status_code == 401


def test_re_analyze_returns_report():
    client = TestClient(app)
    response = client.post(
        "/api/v1/re/analyze",
        files={"file": ("ctx.zip", _zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["kind"] == "zip"
    assert report["hashes"]["sha256"]


def test_re_carve_returns_embedded_artifacts():
    client = TestClient(app)
    payload = b"prefix" + b"PK\x03\x04" + b"A" * 128
    response = client.post(
        "/api/v1/re/carve",
        files={"file": ("image.bin", payload, "application/octet-stream")},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["count"] >= 1
