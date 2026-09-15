from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from .config import Settings
from .models import ProviderName


class ProviderError(RuntimeError):
    """Error returned by an external model provider."""


class ModelProvider:
    name: ProviderName

    async def complete(self, prompt: str, model: str) -> str:
        raise NotImplementedError

    async def complete_stream(self, prompt: str, model: str, on_delta) -> str:
        """Fallback for providers without a streaming adapter."""
        response = await self.complete(prompt, model)
        if response:
            await on_delta(response)
        return response


class LocalProvider(ModelProvider):
    name = ProviderName.local

    async def complete(self, prompt: str, model: str) -> str:
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

    async def complete(self, prompt: str, model: str) -> str:
        url = self.settings.gemini_base_url.rstrip("/") + f"/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8_192},
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Gemini no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta) -> str:
        url = self.settings.gemini_base_url.rstrip("/") + f"/models/{model}:streamGenerateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8_192},
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

    async def complete(self, prompt: str, model: str) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        data = self._response_data(response)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("El proveedor compatible no devolvió texto utilizable.") from exc

    async def complete_stream(self, prompt: str, model: str, on_delta) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
        }
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
    if provider_id == ProviderName.openai_compatible.value:
        return OpenAICompatibleProvider(settings, api_key=api_key, base_url=base_url)
    # Los proveedores declarados por el usuario en la configuración portable
    # siguen el contrato /chat/completions sin exigir cambios de código.
    return OpenAICompatibleProvider(settings, api_key=api_key, base_url=base_url)
