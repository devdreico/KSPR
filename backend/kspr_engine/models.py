from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProviderName(StrEnum):
    local = "local"
    gemini = "gemini"
    openai = "openai"
    groq = "groq"
    deepseek = "deepseek"
    anthropic = "anthropic"
    openrouter = "openrouter"
    opencode_zen = "opencode-zen"
    openai_compatible = "openai-compatible"


class ProcessingMode(StrEnum):
    auto = "auto"
    direct = "direct"
    async_mode = "async"


class SourceFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=0, max_length=2_000_000)

    @field_validator("path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("La ruta debe ser relativa y no puede escapar del contexto")
        return normalized


class AnalysisRequest(BaseModel):
    project_name: str = Field(default="Proyecto sin nombre", min_length=1, max_length=160)
    files: list[SourceFile] = Field(min_length=1, max_length=2_000)
    # Los proveedores integrados tienen nombres conocidos, pero una
    # configuración portable puede declarar cualquier gateway compatible.
    provider: str | None = None
    model: str | None = None
    variant: str | None = Field(default=None, max_length=80)
    effort: str | None = Field(default=None, max_length=50)
    instruction: str | None = Field(default=None, max_length=100_000)
    iterations: int = Field(default=3, ge=1, le=8)
    mode: ProcessingMode = ProcessingMode.auto
    include_source_snapshots: bool = False


class AnalysisSummary(BaseModel):
    project_name: str
    status: str
    provider: str
    model: str
    files_analyzed: int
    total_lines: int
    ui_elements: int
    flows: int
    endpoints: int
    risks: int
    contradictions: int
    iterations_completed: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnalysisArtifact(BaseModel):
    path: str
    title: str
    content: str
    kind: str


class AnalysisResult(BaseModel):
    analysis_id: str
    summary: AnalysisSummary
    report: dict[str, Any]
    artifacts: list[AnalysisArtifact]
    response_text: str = ""


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    stage: str
    message: str
    result: AnalysisResult | None = None
    error: str | None = None


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password: str = Field(min_length=6, max_length=100)


class UserLoginRequest(BaseModel):
    identifier: str = Field(min_length=2, max_length=100)  # username or email
    password: str = Field(min_length=1, max_length=100)


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    primary_technology: str = "TypeScript/React"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class OAuthLoginRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=30)
    token: str = Field(min_length=1)
    email: str = Field(min_length=5, max_length=100)
    username: str | None = Field(default=None, max_length=50)


class MCPTool(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    server: str = ""


class MCPToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    tool_name: str
    result: Any = None
    error: str | None = None


class PluginInfo(BaseModel):
    name: str
    dir_name: str = ""
    version: str = "0.1.0"
    description: str = ""
    tools: list[MCPTool] = Field(default_factory=list)
    enabled: bool = True


class MCPServerConfig(BaseModel):
    type: str = "remote"
    url: str | None = None
    command: list[str] = Field(default_factory=list)
    enabled: bool = True

