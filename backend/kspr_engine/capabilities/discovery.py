"""CapabilityDiscovery — orchestrates adapters to populate the registry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .registry import CapabilityRegistry
from .schemas import CapabilitySchema

if TYPE_CHECKING:
    from ..adapters import BaseAdapter

logger = logging.getLogger(__name__)


class CapabilityDiscovery:
    """Discovery engine that orchestrates adapters to populate the registry."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry
        self._adapters: list[BaseAdapter] = []

    def register_adapter(self, adapter: BaseAdapter) -> None:
        self._adapters.append(adapter)
        logger.info(f"Adapter registered: {adapter.__class__.__name__}")

    def discover_all(self) -> list[CapabilitySchema]:
        """Run discovery on ALL registered adapters."""
        all_capabilities: list[CapabilitySchema] = []
        for adapter in self._adapters:
            try:
                caps = adapter.discover()
                all_capabilities.extend(caps)
                logger.info(
                    f"{adapter.__class__.__name__} found {len(caps)} capabilities"
                )
            except Exception as e:
                logger.error(f"Error in adapter {adapter.__class__.__name__}: {e}")

        for cap in all_capabilities:
            self._registry.register(cap)

        return all_capabilities

    def discover_from(self, adapter_name: str) -> list[CapabilitySchema]:
        """Discovery from a specific adapter by class name."""
        for adapter in self._adapters:
            if adapter.__class__.__name__ == adapter_name:
                caps = adapter.discover()
                for cap in caps:
                    self._registry.register(cap)
                return caps
        logger.warning(f"Adapter not found: {adapter_name}")
        return []

    def refresh(self) -> list[CapabilitySchema]:
        """Refresh all discovery from scratch."""
        self._registry.clear()
        return self.discover_all()
