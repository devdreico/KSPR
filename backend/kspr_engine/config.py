from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KSPR AI - Empresarial"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    default_provider: str = "gemini"
    default_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_transcription_model: str = "gemini-2.5-flash"
    openai_compatible_base_url: str = "https://api.openai.com/v1"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    jwt_secret_key: str = "kspr-secret-default-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    model_config = SettingsConfigDict(env_prefix="KSPR_", env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
