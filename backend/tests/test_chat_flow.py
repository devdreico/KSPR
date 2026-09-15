import pytest
from fastapi.testclient import TestClient
from kspr_engine.config import Settings
from kspr_engine.main import app
from kspr_engine.models import AnalysisRequest


class FakeChatProvider:
    def __init__(self):
        self.prompts: list[str] = []

    async def complete(self, prompt: str, model: str) -> str:
        self.prompts.append(prompt)
        return "Hola, soy KSPR I, el modelo de ingeniería inversa agentica de KSPR."


@pytest.mark.asyncio
async def test_chat_prompt_round_trip_keeps_main_prompt_and_previous_review(monkeypatch):
    from kspr_engine import analyzer

    provider = FakeChatProvider()
    monkeypatch.setattr(analyzer, "get_provider", lambda *_args, **_kwargs: provider)
    request = AnalysisRequest(
        project_name="KSPR chat smoke test",
        files=[{"path": "chat-request.md", "content": "hola"}],
        provider="gemini",
        model="gemini-2.5-flash",
        instruction="MAIN PROMPT DE KSPR I: preséntate con precisión.",
        iterations=2,
    )

    result = await analyzer.analyze(request, Settings())

    assert result.response_text.startswith("Hola, soy KSPR I")
    assert len(provider.prompts) == 2
    assert "Eres KSPR I" in provider.prompts[0]
    assert "preséntate con precisión" in provider.prompts[0]
    assert "RESPUESTA TÉCNICA DE LA ITERACIÓN ANTERIOR" in provider.prompts[1]


def test_http_chat_contract_returns_model_text(monkeypatch):
    from kspr_engine import analyzer

    provider = FakeChatProvider()
    monkeypatch.setattr(analyzer, "get_provider", lambda *_args, **_kwargs: provider)
    response = TestClient(app).post(
        "/api/v1/analyze",
        json={
            "project_name": "KSPR HTTP smoke test",
            "files": [{"path": "chat-request.md", "content": "hola"}],
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "instruction": "Eres KSPR I. Preséntate.",
            "iterations": 1,
            "mode": "direct",
        },
    )

    assert response.status_code == 200
    assert response.json()["response_text"].startswith("Hola, soy KSPR I")


def test_local_chat_contract_can_complete_the_first_ui_smoke_gate():
    response = TestClient(app).post(
        "/api/v1/analyze",
        json={
            "project_name": "KSPR local smoke test",
            "files": [{"path": "chat-request.md", "content": "hola"}],
            "provider": "local",
            "model": "kspr-local",
            "instruction": "Eres KSPR I. Preséntate.",
            "iterations": 1,
            "mode": "direct",
        },
    )

    assert response.status_code == 200
    assert response.json()["response_text"].startswith("Hola, soy KSPR I")


def test_stream_chat_contract_emits_progress_and_result(monkeypatch):
    from kspr_engine import analyzer

    provider = FakeChatProvider()
    monkeypatch.setattr(analyzer, "get_provider", lambda *_args, **_kwargs: provider)
    response = TestClient(app).post(
        "/api/v1/analyze/stream",
        json={
            "project_name": "KSPR SSE smoke test",
            "files": [{"path": "chat-request.md", "content": "hola"}],
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "instruction": "Eres KSPR I. Preséntate.",
            "iterations": 1,
            "mode": "direct",
        },
    )

    assert response.status_code == 200
    assert "\"type\": \"progress\"" in response.text
    assert "\"type\": \"delta\"" in response.text
    assert "\"type\": \"result\"" in response.text
    assert "Hola, soy KSPR I" in response.text
