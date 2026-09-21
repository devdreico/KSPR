"""CapabilityRegistry — central store for discovered capabilities."""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import CapabilitySchema


class CapabilityRegistry:
    """Central registry that stores and manages all discovered capabilities."""

    DEFAULT_PATH = Path.home() / ".kspr" / "capabilities.json"

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or self.DEFAULT_PATH
        self.capabilities: dict[str, CapabilitySchema] = {}
        self._load()

    def _load(self) -> None:
        if self.registry_path.is_file():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                for cap_data in data.get("capabilities", []):
                    cap = CapabilitySchema(**cap_data)
                    self.capabilities[cap.id] = cap
            except Exception:
                pass

    def save(self) -> None:
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "capabilities": [cap.model_dump() for cap in self.capabilities.values()]
            }
            self.registry_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def register(self, cap: CapabilitySchema) -> None:
        self.capabilities[cap.id] = cap

    def unregister(self, cap_id: str) -> bool:
        if cap_id in self.capabilities:
            del self.capabilities[cap_id]
            return True
        return False

    def get(self, cap_id: str) -> CapabilitySchema | None:
        return self.capabilities.get(cap_id)

    def search(self, query: str, category: str | None = None) -> list[CapabilitySchema]:
        query_lower = query.lower()
        results = []
        for cap in self.capabilities.values():
            if query_lower in cap.name.lower() or query_lower in cap.description.lower() or query_lower in cap.id.lower():
                if category and cap.category != category:
                    continue
                results.append(cap)
        return results

    def list_all(self) -> list[CapabilitySchema]:
        return list(self.capabilities.values())

    def list_by_source(self, source_type: str) -> list[CapabilitySchema]:
        return [cap for cap in self.capabilities.values() if cap.source_type == source_type]

    def list_installed(self) -> list[CapabilitySchema]:
        return [cap for cap in self.capabilities.values() if cap.installed]

    def list_enabled(self) -> list[CapabilitySchema]:
        return [cap for cap in self.capabilities.values() if cap.enabled]

    def count(self) -> int:
        return len(self.capabilities)

    def clear(self) -> None:
        self.capabilities.clear()
