"""CapabilityExecutor — executes capabilities by building commands and parsing results."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any

from .schemas import CapabilitySchema, CapabilityResult

logger = logging.getLogger(__name__)


class CapabilityExecutor:
    """Executes capabilities with JSON support and error classification."""

    def __init__(self, default_timeout: int = 30) -> None:
        self._default_timeout = default_timeout

    def execute(
        self,
        cap: CapabilitySchema,
        args: dict[str, Any] | None = None,
        prefer_json: bool = True,
        timeout: int | None = None,
    ) -> CapabilityResult:
        """Execute a capability with arguments."""
        timeout = timeout or self._default_timeout
        start_time = time.monotonic()

        command = list(cap.command)
        if args:
            for key, value in args.items():
                if isinstance(value, bool):
                    if value:
                        command.append(f"--{key}")
                elif value is not None:
                    command.append(f"--{key}")
                    command.append(str(value))

        if prefer_json and cap.returns_json:
            command.append("--json")

        logger.info(f"Executing: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            parsed_output = None
            if cap.returns_json and result.stdout.strip():
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from stdout")

            error_type = None
            error_message = None
            if result.returncode != 0:
                error_type = self._classify_error(result.stderr, result.returncode)
                error_message = result.stderr.strip() or f"Exit code: {result.returncode}"

            return CapabilityResult(
                capability_id=cap.id,
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=parsed_output,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"command": command},
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {timeout}s",
                parsed_output=None,
                error_type="timeout",
                error_message=f"Timeout after {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": command, "timeout": timeout},
            )
        except FileNotFoundError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                parsed_output=None,
                error_type="not_found",
                error_message=f"Command not found: {command[0]}",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except PermissionError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Permission denied",
                parsed_output=None,
                error_type="permission_error",
                error_message="Permission denied",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=cap.id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type="execution_error",
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={"command": command, "exception": type(e).__name__},
            )

    def execute_raw(
        self,
        command: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> CapabilityResult:
        """Execute a raw command not associated with a capability."""
        timeout = timeout or self._default_timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            error_type = None if result.returncode == 0 else "execution_error"
            error_message = None if result.returncode == 0 else result.stderr.strip()

            return CapabilityResult(
                capability_id="raw",
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=None,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"command": command, "raw": True},
            )
        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="raw",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {timeout}s",
                parsed_output=None,
                error_type="timeout",
                error_message=f"Timeout after {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id="raw",
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type="execution_error",
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={"command": command},
            )

    @staticmethod
    def _classify_error(stderr: str, exit_code: int) -> str:
        """Classify the error type from stderr and exit code."""
        stderr_lower = stderr.lower()
        if "not found" in stderr_lower or "no such file" in stderr_lower:
            return "not_found"
        if "permission denied" in stderr_lower or "access denied" in stderr_lower:
            return "permission_error"
        if exit_code == 126:
            return "permission_error"
        if exit_code == 127:
            return "not_found"
        return "execution_error"
