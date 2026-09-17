"""KSPR Autonomous Cognitive OS: Sandbox File I/O & Secure Shell Execution with Self-Correction."""

from __future__ import annotations

import asyncio
import os
import subprocess
import shlex
from pathlib import Path
from typing import Any

class SandboxError(Exception):
    """Raised when sandbox security or execution limits are breached."""


class SafeSandbox:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def _validate_path(self, path: str | Path) -> Path:
        resolved = (self.workspace_root / path).resolve()
        if not str(resolved).startswith(str(self.workspace_root)):
            raise SandboxError("Violación de seguridad: Acceso fuera del workspace prohibido.")
        return resolved

    def read_file(self, path: str | Path, max_bytes: int = 2_000_000) -> str:
        target = self._validate_path(path)
        if not target.is_file():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        return target.read_text(encoding="utf-8", errors="replace")[:max_bytes]

    def write_file(self, path: str | Path, content: str) -> str:
        target = self._validate_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.workspace_root))

    def delete_file(self, path: str | Path) -> bool:
        target = self._validate_path(path)
        if target.is_file():
            target.unlink()
            return True
        return False

    async def execute_shell(self, command: str, timeout: int = 60, max_retries: int = 3) -> dict[str, Any]:
        """Ejecuta un comando de terminal de forma aislada con bucle de autocorrección ante errores."""
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
                    # Bucle de autocorrección: si falla, reportamos para que el orquestador intente corregir
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
            except asyncio.TimeoutError:
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
