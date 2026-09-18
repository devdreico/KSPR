"""KSPR Autonomous Cognitive OS: Dynamic Plugin Ecosystem Loader."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


class PluginLoader:
    def __init__(self, plugins_dir: Path | None = None):
        self.plugins_dir = plugins_dir or (Path.home() / ".kspr" / "plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_plugins: dict[str, Any] = {}

    def load_plugins(self) -> dict[str, Any]:
        """Carga dinámicamente scripts .py desde ~/.kspr/plugins/"""
        if not self.plugins_dir.is_dir():
            return self.loaded_plugins

        for py_file in self.plugins_dir.glob("*.py"):
            plugin_name = py_file.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, str(py_file))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_name] = mod
                    spec.loader.exec_module(mod)
                    self.loaded_plugins[plugin_name] = mod
            except Exception as e:
                print(f"[!] Error cargando plugin {plugin_name}: {e}")
        return self.loaded_plugins
