"""CLIRunner — executes CLI-Anything commands as external processes."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any

from ...capabilities.schemas import CapabilityResult

logger = logging.getLogger(__name__)


class CLIRunner:
    """Executes CLI-Anything commands via subprocess with JSON parsing and error handling."""

    def __init__(self, default_timeout: int = 30):
        self._default_timeout = default_timeout

    def run(
        self,
        command: list[str],
        args: dict[str, Any] | None = None,
        use_json: bool = True,
        timeout: int | None = None,
        cwd: str | None = None,
        capability_id: str = "cli-anything",
    ) -> CapabilityResult:
        """Execute a CLI command and return a normalized CapabilityResult."""
        timeout = timeout or self._default_timeout
        full_command = list(command)

        if args:
            for key, value in args.items():
                if isinstance(value, bool):
                    if value:
                        full_command.append(f"--{key}")
                elif value is not None:
                    full_command.append(f"--{key}")
                    full_command.append(str(value))

        if use_json:
            full_command.append("--json")

        start_time = time.monotonic()

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            parsed_output = None
            if result.stdout.strip():
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.debug("Output is not valid JSON, using raw stdout")

            error_type = None
            error_message = None
            if result.returncode != 0:
                error_type = self._classify_error(result.stderr, result.returncode)
                error_message = result.stderr.strip() or f"Exit code: {result.returncode}"

            return CapabilityResult(
                capability_id=capability_id,
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                parsed_output=parsed_output,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"command": full_command, "json_used": use_json},
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=capability_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {timeout}s",
                parsed_output=None,
                error_type="timeout",
                error_message=f"Timeout after {timeout}s",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except FileNotFoundError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=capability_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command not found: {full_command[0]}",
                parsed_output=None,
                error_type="not_found",
                error_message=f"Command not found: {full_command[0]}",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except PermissionError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=capability_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Permission denied",
                parsed_output=None,
                error_type="permission_error",
                error_message="Permission denied",
                duration_ms=duration_ms,
                metadata={"command": full_command},
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                capability_id=capability_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                parsed_output=None,
                error_type="execution_error",
                error_message=str(e),
                duration_ms=duration_ms,
                metadata={"command": full_command, "exception": type(e).__name__},
            )

    @staticmethod
    def _classify_error(stderr: str, exit_code: int) -> str:
        """Classify the type of error from stderr and exit code."""
        stderr_lower = stderr.lower()
        if "not found" in stderr_lower or "no such command" in stderr_lower:
            return "not_found"
        if "permission denied" in stderr_lower:
            return "permission_error"
        if exit_code == 126:
            return "permission_error"
        if exit_code == 127:
            return "not_found"
        if "timeout" in stderr_lower:
            return "timeout"
        return "execution_error"
