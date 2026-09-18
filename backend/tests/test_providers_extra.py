import httpx
import pytest
from kspr_engine.config import Settings
from kspr_engine.providers import AnthropicProvider, OpenRouterProvider, OpenCodeZenProvider


class FakeAnthropicAsyncClient:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        assert headers.get("x-api-key") == "anthropic-key"
        assert headers.get("anthropic-version") == "2023-06-01"
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "Claude response"}]},
            request=httpx.Request("POST", url),
        )


@pytest.mark.asyncio
async def test_anthropic_provider(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAnthropicAsyncClient)
    provider = AnthropicProvider(Settings(), api_key="anthropic-key")
    res = await provider.complete("Test prompt", "claude-3-5-sonnet-20241022")
    assert res == "Claude response"


class FakeOpenRouterAsyncClient:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        assert headers.get("Authorization") == "Bearer openrouter-key"
        assert headers.get("HTTP-Referer") == "https://kspr.ai"
        assert headers.get("X-Title") == "KSPR AI"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "OpenRouter response"}}]},
            request=httpx.Request("POST", url),
        )


@pytest.mark.asyncio
async def test_openrouter_provider(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeOpenRouterAsyncClient)
    provider = OpenRouterProvider(Settings(), api_key="openrouter-key")
    res = await provider.complete("Test prompt", "openai/gpt-4o")
    assert res == "OpenRouter response"
