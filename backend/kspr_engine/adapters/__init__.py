"""Adapters for different capability sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..capabilities.schemas import CapabilitySchema


class BaseAdapter(ABC):
    """Base class for all capability adapters."""

    SOURCE_TYPE: str = "base"

    @abstractmethod
    def discover(self) -> list[CapabilitySchema]:
        """Discover all capabilities from this adapter's source."""
        ...
