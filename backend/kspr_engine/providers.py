from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from .config import Settings
from .models import ProviderName
from .prompts import KSPR_I_SYSTEM_PROMPT


class ProviderError(RuntimeError):
    """Error returned by an external model provider."""


class ModelProvider:
    name: ProviderName

    async def complete(
        self,
        prompt: str,
        model: str,
        effort: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | dict[str, Any]:
        raise NotImplementedError

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        """Fallback for providers without a streaming adapter."""
        response = await self.complete(prompt, model, effort=effort)
        if isinstance(response, dict):
            response = response.get("text", str(response))
        if response:
            await on_delta(response)
        return response

    def _tools_payload(self, tools: list[dict] | None) -> dict:
        """No-op by default. Providers override per protocol."""
        return {}


class LocalProvider(ModelProvider):
    name = ProviderName.local

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        if "hola" in prompt.lower() or "preséntate" in prompt.lower() or "presentate" in prompt.lower():
            return "Hola, soy KSPR I, el modelo de ingeniería inversa agentica de KSPR. Estoy listo para estudiar la evidencia y devolverte un contexto técnico auditable."
        return "KSPR I está funcionando en modo local de demostración. Conecta Gemini o un gateway compatible para obtener razonamiento LLM sobre el contexto entregado."

    async def list_models(self) -> list[dict[str, Any]]:
        return [{
            "id": "kspr-local",
            "name": "KSPR Local",
            "description": "Respuesta determinista para desarrollo y comprobación de la interfaz.",
        }]


class GeminiProvider(ModelProvider):
    name = ProviderName.gemini

    def __init__(self, settings: Settings, api_key: str | None = None, auth_mode: str = "api_key"):
        self.settings = settings
        self.api_key = api_key
        self.auth_mode = auth_mode

    def _require_key(self) -> str:
        key = (
            self.api_key
            or self.settings.gemini_api_key
            or os.getenv("KSPR_GEMINI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not key:
            raise ProviderError("Configura una API Key de Gemini para conectar el modelo real.")
        return key

    def _headers(self) -> dict[str, str]:
        key = self._require_key()
        authorization = {"Authorization": "Bearer " + key} if self.auth_mode == "bearer" else {"x-goog-api-key": key}
        return {**authorization, "Content-Type": "application/json"}

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.settings.gemini_base_url.rstrip("/") + f"/models/{model}:generateContent"
        tokens = 32768 if effort == "high" else (4096 if effort == "low" else 8192)
        full_text = f"{KSPR_I_SYSTEM_PROMPT}\n\n[INSTRUCCIÓN DEL USUARIO]:\n{prompt}"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": full_text}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": tokens},
        }
        if tools:
            payload["tools"] = {"functionDeclarations": tools}
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            candidate = data["candidates"][0]["content"]
            parts = candidate.get("parts", [])
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            func_parts = [p.get("functionCall", {}) for p in parts if "functionCall" in p]
            if func_parts:
                fc = func_parts[0]
                return {"tool_calls": [{"id": fc.get("name", ""), "function": {"name": fc.get("name", ""), "arguments": fc.get("args", {})}}]}
            return "".join(text_parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Gemini no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        url = self.settings.gemini_base_url.rstrip("/") + f"/models/{model}:streamGenerateContent"
        tokens = 32768 if effort == "high" else (4096 if effort == "low" else 8192)
        full_text = f"{KSPR_I_SYSTEM_PROMPT}\n\n[INSTRUCCIÓN DEL USUARIO]:\n{prompt}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_text}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": tokens},
        }
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180) as client, client.stream("POST", url, params={"alt": "sse"}, headers=self._headers(), json=payload) as response:
                if response.is_error:
                    raw = await response.aread()
                    response._content = raw
                    self._response_data(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        data = json.loads(line[5:].strip())
                        text = "".join(part.get("text", "") for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
                    if text:
                        chunks.append(text)
                        await on_delta(text)
        return "".join(chunks).strip()

    async def list_models(self) -> list[dict[str, Any]]:
        url = self.settings.gemini_base_url.rstrip("/") + "/models"
        models = []
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(20):
                params = {"pageToken": page_token} if page_token else None
                response = await client.get(url, headers=self._headers(), params=params)
                data = self._response_data(response)
                for item in data.get("models", []):
                    if "generateContent" not in item.get("supportedGenerationMethods", []):
                        continue
                    model_id = item.get("name", "").removeprefix("models/")
                    if model_id:
                        models.append({
                            "id": model_id,
                            "name": item.get("displayName") or model_id,
                            "description": item.get("description", ""),
                            "input_token_limit": item.get("inputTokenLimit"),
                            "output_token_limit": item.get("outputTokenLimit"),
                        })
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        return models

    async def transcribe(self, audio: bytes, mime_type: str, model: str | None = None) -> str:
        selected_model = model or self.settings.gemini_transcription_model
        url = self.settings.gemini_base_url.rstrip("/") + f"/models/{selected_model}:generateContent"
        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": "Transcribe este audio en español. Devuelve únicamente la transcripción literal, sin explicaciones."},
                    {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(audio).decode("ascii")}},
                ],
            }],
            "generationConfig": {"temperature": 0},
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Gemini no devolvió una transcripción utilizable.") from exc

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Google devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"Google Gemini respondió {response.status_code}: {detail}")
        return data


class OpenAICompatibleProvider(ModelProvider):
    """Adapter for providers exposing the OpenAI-compatible HTTP contract."""

    name = ProviderName.openai_compatible

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        self.settings = settings
        self.api_key = api_key
        self.base_url = base_url or settings.openai_compatible_base_url

    def _require_key(self) -> str:
        key = self.api_key or os.getenv("KSPR_OPENAI_COMPATIBLE_API_KEY")
        if not key:
            raise ProviderError("Configura una API Key para el proveedor compatible.")
        return key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._require_key(), "Content-Type": "application/json"}

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            msg = data["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {"tool_calls": [
                    {"id": tc["id"], "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", {})}}
                    for tc in msg["tool_calls"]
                ]}
            return msg.get("content", "").strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("El proveedor compatible no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": True,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180) as client, client.stream("POST", url, headers=self._headers(), json=payload) as response:
                if response.is_error:
                    raw = await response.aread()
                    response._content = raw
                    self._response_data(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    value = line[5:].strip()
                    if value == "[DONE]":
                        break
                    try:
                        data = json.loads(value)
                        text = data.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
                    if text:
                        chunks.append(text)
                        await on_delta(text)
        return "".join(chunks).strip()

    async def list_models(self) -> list[dict[str, Any]]:
        url = self.base_url.rstrip("/") + "/models"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers())
        data = self._response_data(response)
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": item.get("name") or model_id,
                    "description": item.get("description", "Modelo expuesto por un endpoint compatible."),
                })
        return models

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"El proveedor compatible devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"Proveedor compatible respondió {response.status_code}: {detail}")
        return data


class OpenAIProvider(ModelProvider):
    """Adapter for OpenAI-compatible APIs (GPT-4, GPT-3.5, etc.)"""

    name = ProviderName.openai

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        self.settings = settings
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de OpenAI para el proveedor openai.")
        return key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._require_key(), "Content-Type": "application/json"}

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            msg = data["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {"tool_calls": [
                    {"id": tc["id"], "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", {})}}
                    for tc in msg["tool_calls"]
                ]}
            return msg.get("content", "").strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("El proveedor OpenAI no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": True,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180) as client, client.stream("POST", url, headers=self._headers(), json=payload) as response:
            if response.is_error:
                raw = await response.aread()
                response._content = raw
                self._response_data(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if value == "[DONE]":
                    break
                try:
                    data = json.loads(value)
                    text = data.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if text:
                    chunks.append(text)
                    await on_delta(text)
        return "".join(chunks).strip()

    async def list_models(self) -> list[dict[str, Any]]:
        url = self.base_url.rstrip("/") + "/models"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers())
        data = self._response_data(response)
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": item.get("name") or model_id,
                    "description": item.get("description", "Modelo expuesto por un endpoint compatible."),
                })
        return models

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"El proveedor OpenAI devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"OpenAI respondió {response.status_code}: {detail}")
        return data


class GroqProvider(ModelProvider):
    """Adapter for Groq API (fast Llama models)."""

    name = ProviderName.groq

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        self.settings = settings
        self.api_key = api_key or settings.groq_api_key
        self.base_url = base_url or settings.groq_base_url

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de Groq para el proveedor groq.")
        return key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._require_key(), "Content-Type": "application/json"}

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            msg = data["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {"tool_calls": [
                    {"id": tc["id"], "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", {})}}
                    for tc in msg["tool_calls"]
                ]}
            return msg.get("content", "").strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("El proveedor Groq no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": True,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180) as client, client.stream("POST", url, headers=self._headers(), json=payload) as response:
            if response.is_error:
                raw = await response.aread()
                response._content = raw
                self._response_data(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if value == "[DONE]":
                    break
                try:
                    data = json.loads(value)
                    text = data.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if text:
                    chunks.append(text)
                    await on_delta(text)
        return "".join(chunks).strip()

    async def list_models(self) -> list[dict[str, Any]]:
        url = self.base_url.rstrip("/") + "/models"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers())
        data = self._response_data(response)
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": item.get("name") or model_id,
                    "description": item.get("description", "Modelo expuesto por un endpoint compatible."),
                })
        return models

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"El proveedor Groq devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"Groq respondió {response.status_code}: {detail}")
        return data


class DeepseekProvider(ModelProvider):
    """Adapter for Deepseek API."""

    name = ProviderName.deepseek

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        self.settings = settings
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de Deepseek para el proveedor deepseek.")
        return key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._require_key(), "Content-Type": "application/json"}

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            msg = data["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {"tool_calls": [
                    {"id": tc["id"], "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", {})}}
                    for tc in msg["tool_calls"]
                ]}
            return msg.get("content", "").strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("El proveedor Deepseek no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta, effort: str | None = None) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": True,
        }
        if effort and effort in {"low", "medium", "high"}:
            payload["reasoning_effort"] = effort
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180) as client, client.stream("POST", url, headers=self._headers(), json=payload) as response:
            if response.is_error:
                raw = await response.aread()
                response._content = raw
                self._response_data(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if value == "[DONE]":
                    break
                try:
                    data = json.loads(value)
                    text = data.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if text:
                    chunks.append(text)
                    await on_delta(text)
        return "".join(chunks).strip()

    async def list_models(self) -> list[dict[str, Any]]:
        url = self.base_url.rstrip("/") + "/models"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers())
        data = self._response_data(response)
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": item.get("name") or model_id,
                    "description": item.get("description", "Modelo expuesto por un endpoint compatible."),
                })
        return models

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"El proveedor Deepseek devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"Deepseek respondió {response.status_code}: {detail}")
        return data


class AnthropicProvider(ModelProvider):
    """Adapter for Anthropic Claude API."""

    name = ProviderName.anthropic

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        self.settings = settings
        self.api_key = api_key or settings.anthropic_api_key or os.getenv("KSPR_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or settings.anthropic_base_url

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de Anthropic para el proveedor anthropic.")
        return key

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._require_key(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def complete(self, prompt: str, model: str, effort: str | None = None, tools: list[dict] | None = None) -> str | dict[str, Any]:
        url = self.base_url.rstrip("/") + "/messages"
        max_tokens = 8192 if effort == "high" else 4096
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": KSPR_I_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }
        if tools:
            payload["tools"] = [
                {"name": t.get("function", {}).get("name", t.get("name", "")), "description": t.get("function", {}).get("description", t.get("description", "")), "input_schema": t.get("function", {}).get("parameters", t.get("input_schema", {}))}
                for t in tools
            ]
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            content = data.get("content", [])
            text_parts = [block.get("text", "") for block in content if block.get("type") == "text"]
            tool_use = [block for block in content if block.get("type") == "tool_use"]
            if tool_use:
                tu = tool_use[0]
                return {"tool_calls": [{"id": tu.get("id", ""), "function": {"name": tu.get("name", ""), "arguments": tu.get("input", {})}}]}
            return "".join(text_parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Anthropic no devolvió texto utilizable.") from exc

    async def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "Anthropic high intelligence model"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "description": "Anthropic fast model"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Anthropic powerful model"},
        ]

    @staticmethod
    def _response_data(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Anthropic devolvió una respuesta no válida ({response.status_code}).") from exc
        if response.is_error:
            detail = data.get("error", {}).get("message", response.text[:300])
            raise ProviderError(f"Anthropic respondió {response.status_code}: {detail}")
        return data


class OpenRouterProvider(OpenAICompatibleProvider):
    """Adapter for OpenRouter API."""

    name = ProviderName.openrouter

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        super().__init__(
            settings,
            api_key=api_key or settings.openrouter_api_key or os.getenv("KSPR_OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url or settings.openrouter_base_url,
        )

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de OpenRouter para el proveedor openrouter.")
        return key

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["HTTP-Referer"] = "https://kspr.ai"
        headers["X-Title"] = "KSPR AI"
        return headers


class OpenCodeZenProvider(OpenAICompatibleProvider):
    """Adapter for OpenCode Zen API."""

    name = ProviderName.opencode_zen

    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None):
        super().__init__(
            settings,
            api_key=api_key or settings.opencode_zen_api_key or os.getenv("KSPR_OPENCODE_ZEN_API_KEY") or os.getenv("OPENCODE_ZEN_API_KEY"),
            base_url=base_url or settings.opencode_zen_base_url,
        )

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise ProviderError("Configura una API Key de OpenCode Zen para el proveedor opencode-zen.")
        return key


def get_provider(
    name: ProviderName | str,
    settings: Settings,
    api_key: str | None = None,
    base_url: str | None = None,
    auth_mode: str = "api_key",
) -> ModelProvider:
    provider_id = str(name)
    if provider_id == ProviderName.local.value:
        return LocalProvider()
    if provider_id == ProviderName.gemini.value:
        return GeminiProvider(settings, api_key=api_key, auth_mode=auth_mode)
    if provider_id == ProviderName.openai.value:
        return OpenAIProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.groq.value:
        return GroqProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.deepseek.value:
        return DeepseekProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.anthropic.value:
        return AnthropicProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.openrouter.value:
        return OpenRouterProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.opencode_zen.value:
        return OpenCodeZenProvider(settings, api_key=api_key, base_url=base_url)
    if provider_id == ProviderName.openai_compatible.value:
        return OpenAICompatibleProvider(settings, api_key=api_key, base_url=base_url)
    return OpenAICompatibleProvider(settings, api_key=api_key, base_url=base_url)
