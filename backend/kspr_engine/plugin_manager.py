"""KSPR Plugin Manager — dynamic plugin loader and tool provider."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .models import MCPTool, PluginInfo


class PluginManagerError(RuntimeError):
    """Error loading or executing a plugin."""


class PluginManager:
    """Scans, loads, and executes tools from plugins in ~/.kspr/plugins/."""

    PLUGINS_DIR = Path.home() / ".kspr" / "plugins"
    MANIFEST_FILE = "kspr_plugin.json"

    def __init__(self, plugins_dir: Path | None = None):
        self.plugins_dir = plugins_dir or self.PLUGINS_DIR
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded: dict[str, Any] = {}
        self.meta: dict[str, PluginInfo] = {}

    def scan_plugins(self) -> list[PluginInfo]:
        plugins: list[PluginInfo] = []
        for plugin_dir in sorted(self.plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            manifest = plugin_dir / self.MANIFEST_FILE
            if manifest.is_file():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    info = PluginInfo(
                        name=data.get("name", plugin_dir.name),
                        dir_name=plugin_dir.name,
                        version=data.get("version", "0.1.0"),
                        description=data.get("description", ""),
                        tools=[
                            MCPTool(
                                name=t.get("name", ""),
                                description=t.get("description", ""),
                                input_schema=t.get("parameters", {}),
                                server=f"plugin:{data.get('name', plugin_dir.name)}",
                            )
                            for t in data.get("tools", [])
                        ],
                        enabled=data.get("enabled", True),
                    )
                    plugins.append(info)
                except Exception:
                    pass
            else:
                py_file = plugin_dir / "__init__.py"
                if not py_file.is_file():
                    py_file = plugin_dir / f"{plugin_dir.name}.py"
                if py_file.is_file():
                    info = PluginInfo(
                        name=plugin_dir.name,
                        dir_name=plugin_dir.name,
                        version="0.1.0",
                        description=f"Auto-detected plugin from {py_file.name}",
                    )
                    plugins.append(info)
        return plugins

    def load_plugin(self, name: str) -> bool:
        if name in self.loaded:
            return True
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.is_dir():
            return False
        manifest = plugin_dir / self.MANIFEST_FILE
        py_file = plugin_dir / "__init__.py"
        if not py_file.is_file():
            py_file = plugin_dir / f"{name}.py"
        if not py_file.is_file():
            return False
        manifest_name = name
        try:
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                manifest_name = data.get("name", name)
            spec = importlib.util.spec_from_file_location(f"kspr_plugin_{name}", str(py_file))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"kspr_plugin_{name}"] = mod
                spec.loader.exec_module(mod)
                self.loaded[manifest_name] = mod
                if manifest.is_file():
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    self.meta[manifest_name] = PluginInfo(
                        name=manifest_name,
                        dir_name=name,
                        version=data.get("version", "0.1.0"),
                        description=data.get("description", ""),
                        tools=[
                            MCPTool(
                                name=t.get("name", ""),
                                description=t.get("description", ""),
                                input_schema=t.get("parameters", {}),
                                server=f"plugin:{manifest_name}",
                            )
                            for t in data.get("tools", [])
                        ],
                        enabled=data.get("enabled", True),
                    )
                else:
                    self.meta[manifest_name] = PluginInfo(name=manifest_name, dir_name=name)
                return True
        except Exception:
            pass
        return False

    def load_all(self) -> int:
        count = 0
        for plugin_info in self.scan_plugins():
            dir_name = plugin_info.dir_name or plugin_info.name
            if plugin_info.enabled and self.load_plugin(dir_name):
                count += 1
        return count

    def get_tools(self) -> list[MCPTool]:
        tools: list[MCPTool] = []
        for name, info in self.meta.items():
            if name in self.loaded:
                tools.extend(info.tools)
        return tools

    def get_tools_definitions(self) -> list[dict[str, Any]]:
        defs: list[dict[str, Any]] = []
        for tool in self.get_tools():
            defs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "properties": {}},
                },
            })
        return defs

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return self.get_tools_definitions()

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        for mod in self.loaded.values():
            executor = getattr(mod, "execute_tool", None)
            if callable(executor):
                try:
                    result = executor(tool_name, arguments)
                    return str(result) if result is not None else ""
                except Exception as e:
                    return f"Plugin error: {e}"
        return f"Tool '{tool_name}' not found in any loaded plugin"

    def unload_plugin(self, name: str) -> bool:
        if name in self.loaded:
            del self.loaded[name]
            if name in self.meta:
                del self.meta[name]
            module_key = f"kspr_plugin_{name}"
            if module_key in sys.modules:
                del sys.modules[module_key]
            return True
        return False

    def get_plugin_info(self, name: str) -> PluginInfo | None:
        return self.meta.get(name)

    def list_loaded(self) -> list[dict[str, Any]]:
        result = []
        for name, info in self.meta.items():
            result.append({
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "tools_count": len(info.tools),
                "loaded": name in self.loaded,
            })
        return result
