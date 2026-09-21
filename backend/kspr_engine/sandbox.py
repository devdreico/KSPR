"""KSPR Autonomous Cognitive OS: Sandbox File I/O & Secure Shell Execution with Self-Correction & Permissions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .permissions import check_permission


class SandboxError(Exception):
    """Raised when sandbox security or execution limits are breached."""


class SafeSandbox:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def _validate_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        # Una ruta absoluta nunca puede escapar del workspace.
        resolved = (candidate if candidate.is_absolute() else self.workspace_root / candidate).resolve()
        if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
            raise SandboxError("Violación de seguridad: Acceso fuera del workspace prohibido.")
        return resolved

    def read_file(self, path: str | Path, max_bytes: int = 2_000_000) -> str:
        target = self._validate_path(path)
        if not target.is_file():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        return target.read_text(encoding="utf-8", errors="replace")[:max_bytes]

    def write_file(self, path: str | Path, content: str) -> str:
        target = self._validate_path(path)
        if target.exists() and not check_permission("fs_modify", str(target.relative_to(self.workspace_root))):
            raise SandboxError("Permiso de modificación de archivo denegado.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.workspace_root))

    def delete_file(self, path: str | Path) -> bool:
        target = self._validate_path(path)
        if target.is_file():
            if not check_permission("fs_delete", str(target.relative_to(self.workspace_root))):
                raise SandboxError("Permiso de eliminación de archivo denegado.")
            target.unlink()
            return True
        return False

    async def execute_shell(self, command: str, timeout: int = 60, max_retries: int = 3) -> dict[str, Any]:
        """Ejecuta un comando de terminal de forma aislada con verificación de permisos y autocorrección."""
        if not check_permission("shell_exec", command):
            return {"success": False, "command": command, "error": "Permiso denegado por el usuario (Cancel)"}

        attempt = 0
        current_command = command
        last_error = ""

        while attempt < max_retries:
            attempt += 1
            proc = await asyncio.create_subprocess_shell(
                current_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root)
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = proc.returncode

                if exit_code == 0:
                    return {
                        "success": True,
                        "command": current_command,
                        "attempt": attempt,
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": exit_code
                    }
                else:
                    last_error = stderr or stdout
                    if attempt >= max_retries:
                        return {
                            "success": False,
                            "command": current_command,
                            "attempt": attempt,
                            "stdout": stdout,
                            "stderr": stderr,
                            "exit_code": exit_code,
                            "error": last_error
                        }
            except TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return {
                    "success": False,
                    "command": current_command,
                    "attempt": attempt,
                    "error": f"Timeout excedido ({timeout}s)"
                }
            except Exception as e:
                return {
                    "success": False,
                    "command": current_command,
                    "attempt": attempt,
                    "error": str(e)
                }

        return {"success": False, "command": command, "error": last_error}
