from __future__ import annotations

from typing import Any

import httpx

from .config import Settings
from .models import AnalysisResult


class SupabaseRepository:
    """Persistencia opcional. KSPR sigue funcionando en modo local sin Supabase."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    async def save_analysis(self, result: AnalysisResult) -> None:
        if not self.enabled:
            return
        key = self.settings.supabase_service_role_key or ""
        headers = {
            "apikey": key,
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        payload: dict[str, Any] = {
            "analysis_id": result.analysis_id,
            "project_name": result.summary.project_name,
            "status": result.summary.status,
            "provider": result.summary.provider,
            "model": result.summary.model,
            "summary": result.summary.model_dump(mode="json"),
            "report": result.report,
            "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
            "response_text": result.response_text,
        }
        url = self.settings.supabase_url.rstrip("/") + "/rest/v1/analyses"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.is_error:
            raise RuntimeError("Supabase no pudo persistir el análisis: " + response.text[:300])
