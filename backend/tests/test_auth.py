import asyncio
import time

from fastapi.testclient import TestClient
from kspr_engine.auth import (
    InvalidCredentials,
    JWTHandler,
    TokenExpired,
    hash_password,
    verify_password,
)
from kspr_engine.config import Settings
from kspr_engine.main import app
from kspr_engine.repository import UserRepository


def test_password_hashing():
    password = "securePassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongPassword", hashed) is False


def test_jwt_creation_and_validation():
    settings = Settings()
    handler = JWTHandler(settings)
    user_id = "test-user-id-123"

    token = handler.create_access_token(user_id)
    assert isinstance(token, str)
    assert len(token) > 0

    decoded_id = handler.decode_token(token)
    assert decoded_id == user_id


def test_jwt_expiration():
    settings = Settings(jwt_expiration_minutes=-1)
    handler = JWTHandler(settings)
    token = handler.create_access_token("test-user")

    time.sleep(0.1)
    try:
        handler.decode_token(token)
        assert False, "Should have raised TokenExpired"
    except TokenExpired as e:
        assert "expirado" in str(e).lower()


def test_jwt_tampering():
    settings = Settings()
    handler = JWTHandler(settings)
    token = handler.create_access_token("test-user")

    tampered_token = token[:-5] + "xxxxx"
    try:
        handler.decode_token(tampered_token)
        assert False, "Should have raised InvalidCredentials"
    except InvalidCredentials as e:
        assert "inválido" in str(e).lower()


def test_register_and_login_flow():
    client = TestClient(app)

    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    }
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 201, response.json()
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    _ = data["access_token"]

    login_response = client.post("/api/v1/auth/login", json={"identifier": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert login_data["user"]["username"] == "testuser"

    login_response2 = client.post("/api/v1/auth/login", json={"identifier": "testuser", "password": "password123"})
    assert login_response2.status_code == 200

    wrong_login = client.post("/api/v1/auth/login", json={"identifier": "test@example.com", "password": "wrong"})
    assert wrong_login.status_code == 401

    nonexistent_login = client.post("/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "password123"})
    assert nonexistent_login.status_code == 401


def test_duplicate_registration_fails():
    client = TestClient(app)

    user_data = {"username": "dupuser", "email": "dup@example.com", "password": "password123"}
    r1 = client.post("/api/v1/auth/register", json=user_data)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=user_data)
    assert r2.status_code == 409
    assert "ya está" in r2.json()["detail"].lower()

    r3 = client.post("/api/v1/auth/register", json={"username": "dupuser", "email": "other@example.com", "password": "password123"})
    assert r3.status_code == 409

    r4 = client.post("/api/v1/auth/register", json={"username": "otheruser", "email": "dup@example.com", "password": "password123"})
    assert r4.status_code == 409


def test_auth_me_endpoint():
    client = TestClient(app)

    register_data = {"username": "meuser", "email": "me@example.com", "password": "password123"}
    reg_resp = client.post("/api/v1/auth/register", json=register_data)
    token = reg_resp.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "meuser"
    assert me_resp.json()["email"] == "me@example.com"

    no_auth = client.get("/api/v1/auth/me")
    assert no_auth.status_code == 401

    bad_token = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert bad_token.status_code == 401


def test_protected_analysis_endpoints_require_auth():
    client = TestClient(app)

    analysis_request = {
        "project_name": "Test Project",
        "files": [{"path": "main.py", "content": "print('hello')"}],
    }

    no_auth = client.post("/api/v1/analyze", json=analysis_request)
    assert no_auth.status_code == 401

    no_auth_stream = client.post("/api/v1/analyze/stream", json=analysis_request)
    assert no_auth_stream.status_code == 401

    no_auth_job = client.post("/api/v1/jobs", json=analysis_request)
    assert no_auth_job.status_code == 401


def test_full_authenticated_analysis_flow():
    client = TestClient(app)

    register_data = {"username": "analyst", "email": "analyst@example.com", "password": "password123"}
    reg_resp = client.post("/api/v1/auth/register", json=register_data)
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    analysis_request = {
        "project_name": "Auth Test Project",
        "files": [{"path": "main.py", "content": "def foo(): return 42"}],
        "provider": "local",
    }

    analyze_resp = client.post("/api/v1/analyze", json=analysis_request, headers=headers)
    assert analyze_resp.status_code == 200, analyze_resp.json()
    assert analyze_resp.json()["summary"]["project_name"] == "Auth Test Project"


def test_oauth_endpoint_returns_501():
    client = TestClient(app)
    register_data = {"username": "oauthuser", "email": "oauth@example.com", "password": "password123"}
    reg_resp = client.post("/api/v1/auth/register", json=register_data)
    token = reg_resp.json()["access_token"]

    oauth_resp = client.post(
        "/api/v1/auth/oauth",
        json={"provider": "google", "token": "fake-google-token", "email": "oauth@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert oauth_resp.status_code == 501
    assert "no implementado" in oauth_resp.json()["detail"].lower()


def test_user_repository_in_memory():
    from kspr_engine.config import Settings

    async def run_test():
        settings = Settings()
        repo = UserRepository(settings)

        password_hash = hash_password("testpass")
        user = await repo.create_user("repouser", "repo@example.com", password_hash)
        assert user.username == "repouser"
        assert user.email == "repo@example.com"

        found = await repo.get_user_by_email("repo@example.com")
        assert found is not None
        assert found["username"] == "repouser"

        found2 = await repo.get_user_by_username("repouser")
        assert found2 is not None
        assert found2["email"] == "repo@example.com"

        found3 = await repo.get_user_by_id(user.id)
        assert found3 is not None
        assert found3.username == "repouser"

        verified = await repo.verify_credentials("repo@example.com", "testpass")
        assert verified is not None
        assert verified.username == "repouser"

        verified2 = await repo.verify_credentials("repouser", "testpass")
        assert verified2 is not None

        failed = await repo.verify_credentials("repo@example.com", "wrongpass")
        assert failed is None

        notfound = await repo.verify_credentials("nonexistent", "testpass")
        assert notfound is None

        email_exists, username_exists = await repo.user_exists("repo@example.com", "other")
        assert email_exists is True
        assert username_exists is False

    asyncio.run(run_test())


def test_health_endpoint_unaffected():
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["name"] == "CASPER AI - Empresarial"