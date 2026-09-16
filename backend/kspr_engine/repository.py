from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Settings
from .models import AnalysisResult, UserProfile

_local_users_store: dict[str, dict] = {}
_local_users_by_id_store: dict[str, dict] = {}


def _get_local_store() -> tuple[dict[str, dict], dict[str, dict]]:
    return _local_users_store, _local_users_by_id_store


class UserRepository:
    """Gestión de usuarios con fallback en memoria y sincronización opcional con Supabase."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    def _get_headers(self) -> dict[str, str]:
        key = self.settings.supabase_service_role_key or ""
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _get_local_users(self) -> tuple[dict[str, dict], dict[str, dict]]:
        return _get_local_store()

    async def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        primary_technology: str = "TypeScript/React",
    ) -> UserProfile:
        user_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "primary_technology": primary_technology,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        local_users, local_users_by_id = self._get_local_users()

        # Store locally (always works)
        local_users[email.lower()] = user_data
        local_users[username.lower()] = user_data
        local_users_by_id[user_id] = user_data

        # Try to persist to Supabase
        if self.supabase_enabled:
            try:
                await self._persist_user_to_supabase(user_data)
            except httpx.HTTPError:
                # Supabase unavailable - local store is source of truth
                pass

        return UserProfile(
            id=user_id,
            username=username,
            email=email,
            primary_technology=primary_technology,
            created_at=now,
        )

    async def _persist_user_to_supabase(self, user_data: dict) -> None:
        url = self.settings.supabase_url.rstrip("/") + "/rest/v1/profiles"
        payload = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "primary_technology": user_data["primary_technology"],
            "password_hash": user_data["password_hash"],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
        if response.is_error:
            raise RuntimeError(f"Supabase no pudo crear usuario: {response.text[:300]}")

    async def get_user_by_email(self, email: str) -> dict | None:
        email_lower = email.lower()
        local_users, _ = self._get_local_users()
        if email_lower in local_users:
            return local_users[email_lower]

        if self.supabase_enabled:
            try:
                return await self._fetch_user_from_supabase("email", email)
            except httpx.HTTPError:
                pass
        return None

    async def get_user_by_username(self, username: str) -> dict | None:
        username_lower = username.lower()
        local_users, _ = self._get_local_users()
        if username_lower in local_users:
            return local_users[username_lower]

        if self.supabase_enabled:
            try:
                return await self._fetch_user_from_supabase("username", username)
            except httpx.HTTPError:
                pass
        return None

    async def get_user_by_id(self, user_id: str) -> UserProfile | None:
        _, local_users_by_id = self._get_local_users()
        if user_id in local_users_by_id:
            u = local_users_by_id[user_id]
            return UserProfile(
                id=u["id"],
                username=u["username"],
                email=u["email"],
                primary_technology=u["primary_technology"],
                created_at=datetime.fromisoformat(u["created_at"]),
            )

        if self.supabase_enabled:
            try:
                user_data = await self._fetch_user_from_supabase("id", user_id)
                if user_data:
                    return UserProfile(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        primary_technology=user_data.get("primary_technology", "TypeScript/React"),
                        created_at=datetime.fromisoformat(user_data["created_at"]),
                    )
            except httpx.HTTPError:
                pass
        return None

    async def _fetch_user_from_supabase(self, field: str, value: str) -> dict | None:
        url = self.settings.supabase_url.rstrip("/") + f"/rest/v1/profiles?{field}=eq.{value}&limit=1"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._get_headers())
        if response.is_error:
            return None
        data = response.json()
        if data:
            user_data = data[0]
            # Cache locally
            local_users, local_users_by_id = self._get_local_users()
            local_users[user_data["email"].lower()] = user_data
            local_users[user_data["username"].lower()] = user_data
            local_users_by_id[user_data["id"]] = user_data
            return user_data
        return None

    async def verify_credentials(self, identifier: str, password: str) -> UserProfile | None:
        from .auth import verify_password

        # Try email first, then username
        user_data = await self.get_user_by_email(identifier)
        if not user_data:
            user_data = await self.get_user_by_username(identifier)

        if not user_data:
            return None

        if not verify_password(password, user_data["password_hash"]):
            return None

        return UserProfile(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            primary_technology=user_data.get("primary_technology", "TypeScript/React"),
            created_at=datetime.fromisoformat(user_data["created_at"]),
        )

    async def user_exists(self, email: str, username: str) -> tuple[bool, bool]:
        email_exists = await self.get_user_by_email(email) is not None
        username_exists = await self.get_user_by_username(username) is not None
        return email_exists, username_exists


class SupabaseRepository:
    """Persistencia opcional. KSPR sigue funcionando en modo local sin Supabase."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    async def save_analysis(self, result: AnalysisResult, user_id: str | None = None) -> None:
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
        if user_id:
            payload["user_id"] = user_id
        url = self.settings.supabase_url.rstrip("/") + "/rest/v1/analyses"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.is_error:
            raise RuntimeError("Supabase no pudo persistir el análisis: " + response.text[:300])
