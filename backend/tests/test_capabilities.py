import os
import tempfile
from pathlib import Path

from kspr_engine.capabilities import CapabilityManager
from kspr_engine.capabilities.discovery import CapabilityDiscovery
from kspr_engine.capabilities.executor import CapabilityExecutor
from kspr_engine.capabilities.loader import CapabilityLoader
from kspr_engine.capabilities.permissions import CapabilityPermissions
from kspr_engine.capabilities.registry import CapabilityRegistry
from kspr_engine.capabilities.schemas import CapabilityResult, CapabilitySchema, CapabilityValidation
from kspr_engine.capabilities.validator import CapabilityValidator


class TestCapabilitySchema:
    def test_create_minimal(self):
        cap = CapabilitySchema(id="test:1", name="Test", source="test")
        assert cap.id == "test:1"
        assert cap.source_type == "native"
        assert cap.installed is False
        assert cap.enabled is True

    def test_create_full(self):
        cap = CapabilitySchema(
            id="cli-any:analyze",
            name="analyze",
            description="Code analyzer",
            source="/usr/bin/analyze",
            source_type="cli-anything",
            category="analysis",
            command=["analyze"],
            arguments={"file": {"type": "string"}},
            returns_json=True,
            requires=["python3"],
            skill_path="/skills/SKILL.md",
            skill_content="# Skill",
            installed=True,
            version="1.0.0",
        )
        assert cap.source_type == "cli-anything"
        assert cap.installed is True
        assert cap.returns_json is True

    def test_result_success(self):
        result = CapabilityResult(
            capability_id="test",
            success=True,
            exit_code=0,
            stdout="ok",
        )
        assert result.success is True
        assert result.exit_code == 0

    def test_result_failure(self):
        result = CapabilityResult(
            capability_id="test",
            success=False,
            exit_code=1,
            error_type="not_found",
            error_message="Not found",
        )
        assert result.success is False
        assert result.error_type == "not_found"

    def test_validation(self):
        v = CapabilityValidation(
            capability_id="test",
            valid=True,
            checks=[{"name": "exit_code", "passed": True, "detail": "ok"}],
            warnings=["slow"],
        )
        assert v.valid is True
        assert len(v.warnings) == 1


class TestCapabilityRegistry:
    def test_register_and_get(self):
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        cap = CapabilitySchema(id="test:1", name="Test", source="test")
        reg.register(cap)
        assert reg.get("test:1") is not None
        assert reg.get("test:1").name == "Test"

    def test_unregister(self):
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        cap = CapabilitySchema(id="test:1", name="Test", source="test")
        reg.register(cap)
        assert reg.unregister("test:1") is True
        assert reg.get("test:1") is None
        assert reg.unregister("nonexistent") is False

    def test_search(self):
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        reg.register(CapabilitySchema(id="a", name="Analyzer", source="test"))
        reg.register(CapabilitySchema(id="b", name="Builder", source="test"))
        results = reg.search("analy")
        assert len(results) == 1
        assert results[0].id == "a"

    def test_list_by_source(self):
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        reg.register(CapabilitySchema(id="a", name="A", source="s1", source_type="cli-anything"))
        reg.register(CapabilitySchema(id="b", name="B", source="s2", source_type="mcp"))
        cli_caps = reg.list_by_source("cli-anything")
        assert len(cli_caps) == 1

    def test_save_and_load(self):
        path = Path(tempfile.mktemp())
        reg = CapabilityRegistry(registry_path=path)
        reg.register(CapabilitySchema(id="x", name="X", source="test", installed=True))
        reg.save()
        reg2 = CapabilityRegistry(registry_path=path)
        assert reg2.get("x") is not None
        os.unlink(str(path))


class TestCapabilityPermissions:
    def test_check_default(self):
        perms = CapabilityPermissions(permissions_path=Path(tempfile.mktemp()))
        assert perms.check("any_cap", "read") is True
        assert perms.check("any_cap", "execute") is False

    def test_grant_and_check(self):
        path = Path(tempfile.mktemp())
        perms = CapabilityPermissions(permissions_path=path)
        perms.grant("cap1", "execute")
        assert perms.check("cap1", "execute") is True
        assert perms.check("cap1", "write") is False

    def test_revoke(self):
        path = Path(tempfile.mktemp())
        perms = CapabilityPermissions(permissions_path=path)
        perms.grant("cap1", "admin")
        perms.revoke("cap1")
        assert perms.check("cap1", "execute") is False

    def test_always_ask(self):
        path = Path(tempfile.mktemp())
        perms = CapabilityPermissions(permissions_path=path)
        assert perms.needs_confirmation("cap1") is False
        perms.set_always_ask("cap1", True)
        assert perms.needs_confirmation("cap1") is True


class TestCapabilityLoader:
    def test_load_skill_md(self):
        content = """---
name: test-skill
description: A test skill
category: utility
command: [test-cmd]
version: 0.1.0
---
# Test Skill

## Commands

| Command | Description |
|---------|-------------|
| `run <file>` | Run a file |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            cap = CapabilityLoader.load_skill_md(f.name)
            os.unlink(f.name)
        assert cap is not None
        assert cap.name == "test-skill"
        assert cap.source_type == "cli-anything"
        assert "run" in cap.arguments

    def test_load_skill_md_nonexistent(self):
        assert CapabilityLoader.load_skill_md("/nonexistent/SKILL.md") is None

    def test_parse_markdown_commands(self):
        body = """
| `analyze <file>` | Analyze a file |
| `lint <dir>` | Lint directory |
"""
        commands = CapabilityLoader._parse_markdown_commands(body)
        assert "analyze" in commands
        assert commands["analyze"]["args"] == ["file"]
        assert "lint" in commands

    def test_enrich_capability(self):
        cap = CapabilitySchema(id="test", name="test", source="test")
        help_info = {"description": "From help", "positional_args": ["arg1"], "options": ["verbose"]}
        enriched = CapabilityLoader.enrich_capability(cap, help_info)
        assert enriched.description == "From help"
        assert "arg1" in enriched.arguments


class TestCapabilityDiscovery:
    def test_discover_all(self):
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        disc = CapabilityDiscovery(reg)
        caps = disc.discover_all()
        assert isinstance(caps, list)

    def test_register_adapter(self):
        from kspr_engine.adapters import BaseAdapter
        reg = CapabilityRegistry(registry_path=Path(tempfile.mktemp()))
        disc = CapabilityDiscovery(reg)

        class MockAdapter(BaseAdapter):
            def discover(self):
                return [CapabilitySchema(id="mock:1", name="Mock", source="mock", source_type="native", installed=True)]

        disc.register_adapter(MockAdapter())
        caps = disc.discover_all()
        assert len(caps) == 1
        assert caps[0].id == "mock:1"


class TestCapabilityExecutor:
    def test_execute_raw(self):
        executor = CapabilityExecutor()
        result = executor.execute_raw(["echo", "hello"])
        assert result.success is True
        assert "hello" in result.stdout

    def test_execute_raw_failure(self):
        executor = CapabilityExecutor()
        result = executor.execute_raw(["false"])
        assert result.success is False
        assert result.exit_code != 0

    def test_classify_error_not_found(self):
        assert CapabilityExecutor._classify_error("command not found", 127) == "not_found"

    def test_classify_error_permission(self):
        assert CapabilityExecutor._classify_error("permission denied", 126) == "permission_error"


class TestCapabilityValidator:
    def test_validate_result_success(self):
        validator = CapabilityValidator()
        result = CapabilityResult(capability_id="t", success=True, exit_code=0)
        v = validator.validate_result(result, expected_exit_code=0)
        assert v.valid is True

    def test_validate_result_wrong_exit(self):
        validator = CapabilityValidator()
        result = CapabilityResult(capability_id="t", success=False, exit_code=1)
        v = validator.validate_result(result, expected_exit_code=0)
        assert v.valid is False

    def test_validate_json_schema(self):
        validator = CapabilityValidator()
        schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
        v = validator.validate_json_schema({"name": "test"}, schema)
        assert v.valid is True

    def test_validate_json_schema_missing_field(self):
        validator = CapabilityValidator()
        schema = {"type": "object", "required": ["name"]}
        v = validator.validate_json_schema({}, schema)
        assert v.valid is False


class TestCapabilityManager:
    def test_initialize(self):
        mgr = CapabilityManager()
        mgr.initialize()
        assert mgr._initialized is True

    def test_initialize_idempotent(self):
        mgr = CapabilityManager()
        mgr.initialize()
        mgr.initialize()
        assert mgr._initialized is True

    def test_get_schemas_for_llm(self):
        mgr = CapabilityManager()
        mgr.initialize()
        schemas = mgr.get_schemas_for_llm()
        assert isinstance(schemas, list)
