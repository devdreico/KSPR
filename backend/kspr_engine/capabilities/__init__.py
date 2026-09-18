"""KSPR Capability Layer — abstraction for discovering, loading, executing, and validating external tools."""

from __future__ import annotations

import logging
from typing import Any

from .schemas import CapabilitySchema, CapabilityResult, CapabilityValidation
from .registry import CapabilityRegistry
from .permissions import CapabilityPermissions
from .loader import CapabilityLoader
from .discovery import CapabilityDiscovery
from .executor import CapabilityExecutor
from .validator import CapabilityValidator

logger = logging.getLogger(__name__)

__all__ = [
    "CapabilitySchema",
    "CapabilityResult",
    "CapabilityValidation",
    "CapabilityRegistry",
    "CapabilityPermissions",
    "CapabilityLoader",
    "CapabilityDiscovery",
    "CapabilityExecutor",
    "CapabilityValidator",
    "CapabilityManager",
]


class CapabilityManager:
    """Central orchestrator for the Capability Layer.

    Coordinates registry, discovery, loader, executor, validator, and permissions.
    Initialized once at shell startup, used by /capabilities and tool calling loop.
    """

    def __init__(self) -> None:
        self.registry = CapabilityRegistry()
        self.discovery = CapabilityDiscovery(self.registry)
        self.loader = CapabilityLoader()
        self.executor = CapabilityExecutor()
        self.validator = CapabilityValidator()
        self.permissions = CapabilityPermissions()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize at shell startup: register adapters, run discovery."""
        if self._initialized:
            return

        try:
            from ..adapters.cli_anything import CLIAnythingAdapter
            adapter = CLIAnythingAdapter()
            if adapter.is_available():
                self.discovery.register_adapter(adapter)
                logger.info("CLI-Anything adapter registered")
        except Exception as e:
            logger.debug(f"CLI-Anything not available: {e}")

        self.discovery.discover_all()
        self._initialized = True
        caps = self.registry.list_installed()
        logger.info(f"CapabilityManager initialized: {len(caps)} capabilities")

    def list_capabilities(self) -> list[CapabilitySchema]:
        return self.registry.list_installed()

    def search(self, query: str) -> list[CapabilitySchema]:
        return self.registry.search(query)

    def get(self, cap_id: str) -> CapabilitySchema | None:
        return self.registry.get(cap_id)

    def execute(
        self,
        cap_id: str,
        args: dict[str, Any] | None = None,
        prefer_json: bool = True,
        timeout: int = 30,
    ) -> CapabilityResult:
        """Execute a capability with permission check and validation."""
        cap = self.registry.get(cap_id)
        if not cap:
            return CapabilityResult(
                capability_id=cap_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Capability not found: {cap_id}",
                parsed_output=None,
                error_type=None,
                error_message=f"Capability not found: {cap_id}",
                duration_ms=0,
                metadata={},
            )

        if not self.permissions.check(cap_id, "execute"):
            granted = self.permissions.prompt_user(cap_id, "execute")
            if not granted:
                return CapabilityResult(
                    capability_id=cap_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Permission denied by user",
                    parsed_output=None,
                    error_type="permission_error",
                    error_message="Permission denied by user",
                    duration_ms=0,
                    metadata={},
                )

        result = self.executor.execute(cap, args or {}, prefer_json, timeout)

        validation = self.validator.validate_result(
            result,
            expect_json=cap.returns_json,
        )
        if validation.warnings:
            for warning in validation.warnings:
                logger.warning(f"Validation: {warning}")

        return result

    def get_schemas_for_llm(self) -> list[dict[str, Any]]:
        """Generate tool schemas for the LLM tool calling loop."""
        schemas: list[dict[str, Any]] = []
        for cap in self.registry.list_installed():
            schema = {
                "type": "function",
                "function": {
                    "name": f"capability_{cap.id.replace(':', '_')}",
                    "description": cap.description,
                    "parameters": {
                        "type": "object",
                        "properties": cap.arguments,
                        "required": [
                            k for k, v in cap.arguments.items()
                            if isinstance(v, dict) and v.get("required", False)
                        ],
                    },
                },
            }
            schemas.append(schema)
        return schemas

    def refresh(self) -> list[CapabilitySchema]:
        return self.discovery.refresh()
