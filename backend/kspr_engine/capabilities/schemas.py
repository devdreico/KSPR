"""Capability schemas — normalized data models for all capability types."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CapabilitySchema(BaseModel):
    """Normalized representation of a discoverable capability."""

    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    source: str = Field(min_length=1, max_length=200)
    source_type: str = Field(default="native", pattern=r"^(cli-anything|mcp|plugin|native)$")
    category: str = ""
    command: list[str] = Field(default_factory=list)
    arguments: dict[str, Any] = Field(default_factory=dict)
    returns_json: bool = True
    requires: list[str] = Field(default_factory=list)
    skill_path: str | None = None
    skill_content: str | None = None
    installed: bool = False
    version: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityResult(BaseModel):
    """Normalized result from a capability execution."""

    capability_id: str
    success: bool
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    parsed_output: Any = None
    error_type: str | None = None
    error_message: str | None = None
    duration_ms: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityValidation(BaseModel):
    """Result of post-execution validation."""

    capability_id: str
    valid: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
