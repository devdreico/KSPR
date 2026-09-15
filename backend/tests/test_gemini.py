import httpx
import pytest
from kspr_engine.config import Settings
from kspr_engine.providers import GeminiProvider, OpenAICompatibleProvider


class FakeAsyncClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        assert "key=" not in url
        assert headers.get("x-goog-api-key", headers.get("Authorization")) in {"test-key", "Bearer oauth-token"}
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Hola, soy KSPR I."}]}}]},
            request=httpx.Request("POST", url),
        )

    async def get(self, url, headers, params=None):
        assert headers["Authorization"] == "Bearer compatible-key"
        return httpx.Response(
            200,
            json={"data": [{"id": "demo-model", "name": "Demo model"}]},
            request=httpx.Request("GET", url),
        )


@pytest.mark.asyncio
async def test_gemini_uses_official_api_key_header(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = GeminiProvider(Settings(), api_key="test-key")
    assert await provider.complete("Preséntate", "gemini-2.5-flash") == "Hola, soy KSPR I."


@pytest.mark.asyncio
async def test_gemini_accepts_oauth_bearer_mode(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = GeminiProvider(Settings(), api_key="oauth-token", auth_mode="bearer")
    assert await provider.complete("Preséntate", "gemini-2.5-flash") == "Hola, soy KSPR I."


@pytest.mark.asyncio
async def test_openai_compatible_provider_discovers_models(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = OpenAICompatibleProvider(Settings(), api_key="compatible-key", base_url="https://gateway.example/v1")
    assert (await provider.list_models())[0]["id"] == "demo-model"
