"""CapabilityValidator — validates results from capability execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import CapabilityResult, CapabilityValidation


class CapabilityValidator:
    """Validates capability execution results against expectations."""

    def validate_result(
        self,
        result: CapabilityResult,
        expected_exit_code: int = 0,
        expect_json: bool = False,
        json_schema: dict | None = None,
    ) -> CapabilityValidation:
        """Validate a CapabilityResult against expectations."""
        checks: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Check exit code
        exit_ok = result.exit_code == expected_exit_code
        checks.append({
            "name": "exit_code",
            "passed": exit_ok,
            "detail": f"got {result.exit_code}, expected {expected_exit_code}",
        })

        # Check JSON output
        if expect_json:
            json_ok = result.parsed_output is not None
            checks.append({
                "name": "json_output",
                "passed": json_ok,
                "detail": "parsed_output is not None" if json_ok else "parsed_output is None",
            })

            if json_ok and json_schema:
                schema_issues = self._validate_json_schema(
                    result.parsed_output, json_schema
                )
                checks.append({
                    "name": "json_schema",
                    "passed": len(schema_issues) == 0,
                    "detail": "; ".join(schema_issues) if schema_issues else "valid",
                })

        # Warnings
        if result.stderr and result.success:
            warnings.append("Command succeeded but produced stderr output")
        if result.duration_ms > 10000:
            warnings.append(f"High execution time: {result.duration_ms:.0f}ms")

        return CapabilityValidation(
            capability_id=result.capability_id,
            valid=all(c["passed"] for c in checks),
            checks=checks,
            warnings=warnings,
        )

    def validate_file_output(
        self,
        result: CapabilityResult,
        expected_files: list[str] | None = None,
        base_dir: str | None = None,
    ) -> CapabilityValidation:
        """Validate that expected files exist after execution."""
        checks: list[dict[str, Any]] = []
        warnings: list[str] = []

        if expected_files and base_dir:
            base = Path(base_dir)
            for filename in expected_files:
                path = base / filename
                exists = path.exists()
                checks.append({
                    "name": f"file:{filename}",
                    "passed": exists,
                    "detail": f"{path} exists" if exists else f"{path} not found",
                })

        return CapabilityValidation(
            capability_id=result.capability_id,
            valid=all(c["passed"] for c in checks),
            checks=checks,
            warnings=warnings,
        )

    def validate_json_schema(
        self,
        data: Any,
        schema: dict,
    ) -> CapabilityValidation:
        """Validate data against a basic JSON Schema."""
        issues = self._validate_json_schema(data, schema)
        return CapabilityValidation(
            capability_id="json_schema",
            valid=len(issues) == 0,
            checks=[{
                "name": "json_schema",
                "passed": len(issues) == 0,
                "detail": "; ".join(issues) if issues else "valid",
            }],
            warnings=[],
        )

    @staticmethod
    def _validate_json_schema(data: Any, schema: dict) -> list[str]:
        """Basic JSON Schema validation (required + type)."""
        issues: list[str] = []
        if not isinstance(data, dict):
            issues.append(f"Expected object, got {type(data).__name__}")
            return issues

        for field in schema.get("required", []):
            if field not in data:
                issues.append(f"Missing required field: {field}")

        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data:
                expected_type = field_schema.get("type")
                actual_value = data[field]
                if expected_type == "string" and not isinstance(actual_value, str):
                    issues.append(f"Field '{field}' must be string")
                elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                    issues.append(f"Field '{field}' must be number")
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    issues.append(f"Field '{field}' must be boolean")

        return issues
