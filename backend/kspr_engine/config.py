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
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_compatible_base_url: str = "https://api.openai.com/v1"
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    opencode_zen_api_key: str | None = None
    opencode_zen_base_url: str = "https://zen.opencode.ai/api/v1"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    # Sin valor por defecto hardcodeado: auth.py genera/lee una clave local
    # persistente en ~/.kspr/jwt_secret.key cuando no se configura explícitamente.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440
    mcp_servers: str = '{}'
    plugins_dir: str = '~/.kspr/plugins'
    plugins_enabled: str = 'true'

    model_config = SettingsConfigDict(env_prefix="KSPR_", env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
