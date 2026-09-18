"""CLIAnythingDetector — finds installed CLI-Anything harnesses on the system."""

from __future__ import annotations

import importlib.metadata
import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class CLIAnythingDetector:
    """Detects installed CLI-Anything harnesses using multiple strategies."""

    CLI_HUB_DIR = Path.home() / ".cli-hub"
    INSTALLED_JSON = CLI_HUB_DIR / "installed.json"

    def detect_installed(self) -> list[dict]:
        """Run all detection strategies and return unified list."""
        harnesses: list[dict] = []
        harnesses.extend(self._detect_from_path())
        harnesses.extend(self._detect_from_hub_json())
        harnesses.extend(self._detect_from_pip())

        seen: set[str] = set()
        unique: list[dict] = []
        for h in harnesses:
            name = h.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique.append(h)

        logger.info(f"Detected {len(unique)} CLI-Anything harnesses")
        return unique

    def _detect_from_path(self) -> list[dict]:
        """Find executables starting with 'cli-anything-' in PATH."""
        harnesses: list[dict] = []
        prefixes = ["cli-anything-", "cli-hub-"]
        for path_dir in shutil.which("path") or []:
            pass
        # Search common bin directories
        for bin_dir in [Path("/usr/local/bin"), Path.home() / ".local" / "bin"]:
            if not bin_dir.is_dir():
                continue
            for prefix in prefixes:
                for executable in bin_dir.glob(f"{prefix}*"):
                    if executable.is_file():
                        harnesses.append({
                            "name": executable.name,
                            "command": [str(executable)],
                            "source": "path",
                            "version": "unknown",
                        })
        return harnesses

    def _detect_from_hub_json(self) -> list[dict]:
        """Read ~/.cli-hub/installed.json if it exists."""
        if not self.INSTALLED_JSON.exists():
            return []
        try:
            data = json.loads(self.INSTALLED_JSON.read_text(encoding="utf-8"))
            harnesses: list[dict] = []
            for name, info in data.get("installed", {}).items():
                harnesses.append({
                    "name": name,
                    "command": info.get("command", [name]),
                    "source": "cli-hub",
                    "version": info.get("version", "0.0.0"),
                    "registry_path": info.get("registry_path"),
                })
            return harnesses
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error reading installed.json: {e}")
            return []

    def _detect_from_pip(self) -> list[dict]:
        """Find pip packages containing 'cli-anything' or 'cli-hub' in name."""
        harnesses: list[dict] = []
        try:
            for dist in importlib.metadata.distributions():
                name = dist.metadata["Name"]
                if "cli-anything" in name.lower() or "cli-hub" in name.lower():
                    harnesses.append({
                        "name": name,
                        "command": [name.replace("-", "_")],
                        "source": "pip",
                        "version": dist.metadata["Version"],
                    })
        except Exception as e:
            logger.debug(f"Error scanning pip: {e}")
        return harnesses

    def get_registry_path(self, harness_name: str) -> Path | None:
        """Find registry.json for a specific harness."""
        search_paths = [
            self.CLI_HUB_DIR / harness_name / "registry.json",
            Path(f"/usr/local/lib/{harness_name}/registry.json"),
            Path.home() / ".local" / "share" / harness_name / "registry.json",
        ]
        for path in search_paths:
            if path.exists():
                return path
        return None

    def detect_executable(self, entry_point: str) -> str | None:
        """Check if a specific entry_point is available."""
        return shutil.which(entry_point)
