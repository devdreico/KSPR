"""CLIAnythingAdapter — discovers and executes CLI-Anything capabilities."""

from __future__ import annotations

import json
import logging

from ...capabilities.loader import CapabilityLoader
from ...capabilities.schemas import CapabilitySchema
from .. import BaseAdapter
from .detector import CLIAnythingDetector
from .parser import SKILLParser
from .runner import CLIRunner

logger = logging.getLogger(__name__)


class CLIAnythingAdapter(BaseAdapter):
    """Adapter to discover and execute CLI-Anything capabilities.

    KSPR I never imports CLI-Anything modules directly.
    All interaction is via filesystem reads and subprocess calls.
    """

    SOURCE_TYPE = "cli-anything"

    def __init__(self) -> None:
        self._detector = CLIAnythingDetector()
        self._parser = SKILLParser()
        self._runner = CLIRunner()

    def is_available(self) -> bool:
        """Check if at least one CLI-Anything harness is installed."""
        return len(self._detector.detect_installed()) > 0

    def discover(self) -> list[CapabilitySchema]:
        """Discover all CLI-Anything capabilities."""
        capabilities: list[CapabilitySchema] = []
        harnesses = self._detector.detect_installed()

        for harness in harnesses:
            try:
                caps = self._discover_from_harness(harness)
                capabilities.extend(caps)
            except Exception as e:
                logger.error(
                    f"Error discovering from harness {harness['name']}: {e}"
                )

        logger.info(
            f"CLI-Anything: {len(capabilities)} capabilities from "
            f"{len(harnesses)} harnesses"
        )
        return capabilities

    def _discover_from_harness(self, harness: dict) -> list[CapabilitySchema]:
        """Discover capabilities from a specific harness."""
        capabilities: list[CapabilitySchema] = []
        registry_path = self._detector.get_registry_path(harness["name"])
        if registry_path:
            capabilities.extend(self._discover_from_registry(registry_path, harness))
        else:
            capabilities.extend(self._discover_from_help(harness))
        return capabilities

    def _discover_from_registry(
        self, registry_path, harness: dict
    ) -> list[CapabilitySchema]:
        """Discover capabilities from a registry.json file."""
        capabilities: list[CapabilitySchema] = []
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            for skill_info in data.get("skills", {}).values():
                skill_path = skill_info.get("skill_path")
                if skill_path:
                    cap = self._parser.parse_skill_md(skill_path)
                    if cap:
                        cap.source = harness["name"]
                        cap.metadata["harness_name"] = harness["name"]
                        cap.metadata["harness_version"] = harness.get("version")
                        capabilities.append(cap)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error reading registry {registry_path}: {e}")
        return capabilities

    def _discover_from_help(self, harness: dict) -> list[CapabilitySchema]:
        """Discover capabilities by running --help."""
        command = harness.get("command", [harness["name"]])
        help_info = CapabilityLoader.load_cli_help(command)

        if "error" in help_info:
            return []

        cap = CapabilitySchema(
            id=f"cli-any:{harness['name']}",
            name=harness["name"],
            description=help_info.get("description", "CLI-Anything harness"),
            source=harness["name"],
            source_type="cli-anything",
            category="utility",
            command=command,
            arguments={},
            returns_json=False,
            requires=[],
            skill_path=None,
            skill_content=None,
            installed=True,
            version=harness.get("version", "0.0.0"),
            metadata={"from_help": True},
        )
        cap = CapabilityLoader.enrich_capability(cap, help_info)
        return [cap]

    def run(
        self,
        command: list[str],
        args: dict | None = None,
        use_json: bool = True,
        timeout: int = 30,
        capability_id: str = "cli-anything",
    ):
        """Proxy to CLIRunner for command execution."""
        return self._runner.run(command, args, use_json, timeout, capability_id=capability_id)
