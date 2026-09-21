import json

from kspr_engine.plugin_manager import PluginManager


class TestPluginManager:
    def test_scan_plugins_empty(self, tmp_path):
        pm = PluginManager(tmp_path)
        plugins = pm.scan_plugins()
        assert plugins == []

    def test_scan_plugins_finds_valid_plugin(self, tmp_path):
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "tools": [
                {"name": "test_tool", "description": "Does testing", "parameters": {"type": "object", "properties": {"input": {"type": "string"}}}}
            ]
        }
        (plugin_dir / "kspr_plugin.json").write_text(json.dumps(manifest))
        pm = PluginManager(tmp_path)
        plugins = pm.scan_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "test_plugin"
        assert plugins[0].version == "1.0.0"
        assert len(plugins[0].tools) == 1
        assert plugins[0].tools[0].name == "test_tool"

    def test_scan_plugins_skips_invalid(self, tmp_path):
        bad_dir = tmp_path / "bad_plugin"
        bad_dir.mkdir()
        (bad_dir / "kspr_plugin.json").write_text("not json")
        pm = PluginManager(tmp_path)
        plugins = pm.scan_plugins()
        assert plugins == []

    def test_load_all(self, tmp_path):
        plugin_dir = tmp_path / "loader_test"
        plugin_dir.mkdir()
        manifest = {"name": "loader", "version": "1.0", "description": "", "tools": []}
        (plugin_dir / "kspr_plugin.json").write_text(json.dumps(manifest))
        (plugin_dir / "__init__.py").write_text("def execute_tool(name, args): return 'ok'")
        pm = PluginManager(tmp_path)
        count = pm.load_all()
        assert count == 1

    def test_get_tool_schemas(self, tmp_path):
        plugin_dir = tmp_path / "schema_test"
        plugin_dir.mkdir()
        manifest = {
            "name": "schema_plug",
            "version": "1.0",
            "description": "",
            "tools": [{"name": "my_tool", "description": "A tool", "parameters": {"type": "object"}}]
        }
        (plugin_dir / "kspr_plugin.json").write_text(json.dumps(manifest))
        (plugin_dir / "__init__.py").write_text("")
        pm = PluginManager(tmp_path)
        pm.load_all()
        schemas = pm.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "my_tool"

    def test_get_plugin_info(self, tmp_path):
        plugin_dir = tmp_path / "info_test"
        plugin_dir.mkdir()
        manifest = {"name": "info_plug", "version": "2.0", "description": "Info plugin", "tools": []}
        (plugin_dir / "kspr_plugin.json").write_text(json.dumps(manifest))
        (plugin_dir / "__init__.py").write_text("")
        pm = PluginManager(tmp_path)
        pm.load_all()
        info = pm.get_plugin_info("info_plug")
        assert info is not None
        assert info.version == "2.0"
        assert pm.get_plugin_info("nonexistent") is None

    def test_execute_tool_no_plugins(self, tmp_path):
        pm = PluginManager(tmp_path)
        result = pm.execute_tool("any_tool", {})
        assert "not found" in result.lower()

    def test_execute_tool_delegates(self, tmp_path):
        plugin_dir = tmp_path / "exec_test"
        plugin_dir.mkdir()
        manifest = {"name": "exec_plug", "version": "1.0", "description": "", "tools": [{"name": "run", "description": ""}]}
        (plugin_dir / "kspr_plugin.json").write_text(json.dumps(manifest))
        (plugin_dir / "__init__.py").write_text("def execute_tool(name, args): return f'executed:{name}:{args}'")
        pm = PluginManager(tmp_path)
        pm.load_all()
        result = pm.execute_tool("run", {"x": 1})
        assert "executed:run" in result
