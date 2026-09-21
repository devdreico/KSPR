"""KSPR Autonomous Cognitive OS: Sensitive Permission Guard (Accept Once | Accept Always | Cancel)."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".kspr"
PERMISSIONS_FILE = CONFIG_DIR / "permissions.json"


def load_permissions() -> dict[str, str]:
    if PERMISSIONS_FILE.is_file():
        try:
            return json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_permissions(perms: dict[str, str]) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PERMISSIONS_FILE.write_text(json.dumps(perms, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[!] No se pudieron guardar los permisos: {e}")


def check_permission(action_type: str, target: str) -> bool:
    """Verifica si una acción sensible tiene permiso autorizado (Accept Always)."""
    perms = load_permissions()
    key = f"{action_type}:{target}"
    if perms.get(key) == "always":
        return True

    # Prompt user interactively
    print("\n\033[95m┌─ [ 🛡️ KSPR Security & Privilege Guard ] ─────────────────────────────────────────┐\033[0m")
    print(f"\033[95m│\033[0m  \033[1mAcción protegida solicitada:\033[0m {action_type}")
    print(f"\033[95m│\033[0m  \033[1mObjetivo / Comando:\033[0m {target}")
    print("\033[95m├──────────────────────────────────────────────────────────────────────────────────┤\033[0m")
    print("\033[95m│\033[0m  \033[32m[1] Accept Once\033[0m    (Permitir solo para esta ejecución)")
    print("\033[95m│\033[0m  \033[36m[2] Accept Always\033[0m  (Autorizar permanentemente)")
    print("\033[95m│\033[0m  \033[31m[3] Cancel\033[0m         (Abortar de forma segura)")
    print("\033[95m└──────────────────────────────────────────────────────────────────────────────────┘\033[0m")

    try:
        choice = input("\033[1mSelecciona opción [1/2/3]: \033[0m").strip()
    except (KeyboardInterrupt, EOFError):
        choice = "3"

    if choice == "1":
        return True
    elif choice == "2":
        perms[key] = "always"
        save_permissions(perms)
        print("\033[32m[✓] Permiso guardado como 'Accept Always'.\033[0m")
        return True
    else:
        print("\033[31m[✕] Operación abortada por el usuario (Cancel).\033[0m")
        return False
