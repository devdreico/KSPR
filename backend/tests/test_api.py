import io
import zipfile

from fastapi.testclient import TestClient
from kspr_engine.jobs import JobStore
from kspr_engine.main import app


def test_health_and_safe_zip_ingestion():
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["name"].startswith("KSPR")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("src/form.py", "def submit():\n    pass\n")
        zipped.writestr("../unsafe.py", "ignored")
    response = client.post(
        "/api/v1/ingest/archive",
        files={"file": ("context.zip", archive.getvalue(), "application/zip")},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_transcription_has_a_safe_local_fallback():
    client = TestClient(app)
    response = client.post(
        "/api/v1/transcribe",
        files={"file": ("voice.webm", b"not-a-real-audio-file", "audio/webm")},
    )
    assert response.status_code == 503
    assert "reconocimiento de voz" in response.json()["detail"]


def test_provider_catalog_reports_missing_credentials_without_crashing():
    client = TestClient(app)
    response = client.get("/api/v1/providers/status", params={"provider": "openai-compatible"})
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["provider"] == "openai-compatible"


def test_imported_custom_provider_uses_the_compatible_contract():
    response = TestClient(app).get("/api/v1/providers/status", params={"provider": "my-gateway"})
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["provider"] == "my-gateway"


def test_job_store_can_cancel_queued_work():
    store = JobStore()
    job = store.create()
    assert store.cancel(job.job_id) is True
    assert store.get(job.job_id).status == "cancelled"
    assert store.cancel(job.job_id) is False
