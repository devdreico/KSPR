"""CapabilityPermissions — access control for capability execution."""

from __future__ import annotations

import json
from pathlib import Path

LEVELS = {"read": 0, "execute": 1, "write": 2, "admin": 3}


class CapabilityPermissions:
    """Controls which capabilities can be executed and at what level."""

    DEFAULT_PATH = Path.home() / ".kspr" / "capability_permissions.json"

    def __init__(self, permissions_path: Path | None = None):
        self.permissions_path = permissions_path or self.DEFAULT_PATH
        self.allowed: dict[str, int] = {}
        self.always_ask: list[str] = []
        self._load()

    def _load(self) -> None:
        if self.permissions_path.is_file():
            try:
                data = json.loads(self.permissions_path.read_text(encoding="utf-8"))
                self.allowed = data.get("allowed", {})
                self.always_ask = data.get("always_ask", [])
            except Exception:
                pass

    def _save(self) -> None:
        try:
            self.permissions_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"allowed": self.allowed, "always_ask": self.always_ask}
            self.permissions_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def check(self, cap_id: str, required_level: str = "execute") -> bool:
        required = LEVELS.get(required_level, 1)
        current = self.allowed.get(cap_id, 0)
        return current >= required

    def grant(self, cap_id: str, level: str = "execute") -> None:
        self.allowed[cap_id] = LEVELS.get(level, 1)
        self._save()

    def revoke(self, cap_id: str) -> None:
        if cap_id in self.allowed:
            del self.allowed[cap_id]
            self._save()

    def set_always_ask(self, cap_id: str, always: bool = True) -> None:
        if always and cap_id not in self.always_ask:
            self.always_ask.append(cap_id)
        elif not always and cap_id in self.always_ask:
            self.always_ask.remove(cap_id)
        self._save()

    def needs_confirmation(self, cap_id: str) -> bool:
        return cap_id in self.always_ask

    def prompt_user(self, cap_id: str, action: str = "execute") -> bool:
        print(f"\n[!] Permission required: {action} on '{cap_id}'")
        print("    [y] Accept Once  [a] Accept Always  [n] Cancel")
        try:
            choice = input("    > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if choice == "y":
            return True
        elif choice == "a":
            self.grant(cap_id, "admin")
            return True
        return False
