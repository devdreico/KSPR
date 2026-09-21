
import httpx
import pytest
from kspr_engine.config import Settings
from kspr_engine.providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
)


class FakeAsyncClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        return httpx.Response(200, json=self.kwargs.get("response_json", {}), request=httpx.Request("POST", url))


class TestGeminiToolCalling:
    @pytest.mark.asyncio
    async def test_complete_returns_tool_calls(self, monkeypatch):
        response_json = {
            "candidates": [{"content": {"parts": [
                {"functionCall": {"name": "read_file", "args": {"path": "/etc/passwd"}}}
            ]}}]
        }
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = GeminiProvider(Settings(), api_key="test-key")
        tools = [{"type": "function", "function": {"name": "read_file", "description": "Read file"}}]
        result = await provider.complete("read /etc/passwd", "gemini-2.5-flash", tools=tools)
        assert isinstance(result, dict)
        assert "tool_calls" in result
        assert result["tool_calls"][0]["function"]["name"] == "read_file"

    @pytest.mark.asyncio
    async def test_complete_returns_text_when_no_tool_use(self, monkeypatch):
        response_json = {"candidates": [{"content": {"parts": [{"text": "Hello!"}]}}]}
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = GeminiProvider(Settings(), api_key="test-key")
        result = await provider.complete("hi", "gemini-2.5-flash")
        assert isinstance(result, str)
        assert result == "Hello!"


class TestOpenAIToolCalling:
    @pytest.mark.asyncio
    async def test_complete_returns_tool_calls(self, monkeypatch):
        response_json = {
            "choices": [{"message": {
                "tool_calls": [{"id": "call_1", "function": {"name": "search", "arguments": '{"query":"test"}'}}]
            }}]
        }
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = OpenAICompatibleProvider(Settings(), api_key="key", base_url="https://api.openai.com/v1")
        tools = [{"type": "function", "function": {"name": "search", "description": "Search web"}}]
        result = await provider.complete("search test", "gpt-4", tools=tools)
        assert isinstance(result, dict)
        assert result["tool_calls"][0]["function"]["name"] == "search"

    @pytest.mark.asyncio
    async def test_complete_returns_text_when_no_tool_calls(self, monkeypatch):
        response_json = {"choices": [{"message": {"content": "Sure!"}}]}
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = OpenAICompatibleProvider(Settings(), api_key="key", base_url="https://api.openai.com/v1")
        result = await provider.complete("hi", "gpt-4")
        assert isinstance(result, str)
        assert result == "Sure!"


class TestAnthropicToolCalling:
    @pytest.mark.asyncio
    async def test_complete_returns_tool_use(self, monkeypatch):
        response_json = {
            "content": [
                {"type": "tool_use", "id": "tu_1", "name": "execute_code", "input": {"code": "print(1)"}}
            ]
        }
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = AnthropicProvider(Settings(), api_key="test-key")
        tools = [{"type": "function", "function": {"name": "execute_code", "description": "Run code"}}]
        result = await provider.complete("run code", "claude-3-5-sonnet-20241022", tools=tools)
        assert isinstance(result, dict)
        assert result["tool_calls"][0]["function"]["name"] == "execute_code"

    @pytest.mark.asyncio
    async def test_complete_returns_text_when_no_tool_use(self, monkeypatch):
        response_json = {"content": [{"type": "text", "text": "Done."}]}
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient(response_json=response_json))
        provider = AnthropicProvider(Settings(), api_key="test-key")
        result = await provider.complete("hi", "claude-3-5-sonnet-20241022")
        assert isinstance(result, str)
        assert result == "Done."
