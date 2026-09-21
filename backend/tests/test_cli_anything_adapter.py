import os
import tempfile

from kspr_engine.adapters.cli_anything import CLIAnythingAdapter
from kspr_engine.adapters.cli_anything.detector import CLIAnythingDetector
from kspr_engine.adapters.cli_anything.parser import SKILLParser
from kspr_engine.adapters.cli_anything.runner import CLIRunner


class TestCLIAnythingDetector:
    def test_detect_installed(self):
        detector = CLIAnythingDetector()
        harnesses = detector.detect_installed()
        assert isinstance(harnesses, list)

    def test_detect_from_path(self):
        detector = CLIAnythingDetector()
        harnesses = detector._detect_from_path()
        assert isinstance(harnesses, list)

    def test_detect_from_hub_json_no_file(self):
        detector = CLIAnythingDetector()
        harnesses = detector._detect_from_hub_json()
        assert isinstance(harnesses, list)

    def test_detect_from_pip(self):
        detector = CLIAnythingDetector()
        harnesses = detector._detect_from_pip()
        assert isinstance(harnesses, list)

    def test_get_registry_path_nonexistent(self):
        detector = CLIAnythingDetector()
        path = detector.get_registry_path("nonexistent-harness-xyz")
        assert path is None


class TestSKILLParser:
    def test_parse_skill_md(self):
        content = """---
name: test-skill
description: A test skill
category: utility
command: [test-cmd]
version: 0.1.0
---
# Test

| Command | Description |
|---------|-------------|
| `run <file>` | Run a file |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            cap = SKILLParser.parse_skill_md(f.name)
            os.unlink(f.name)
        assert cap is not None
        assert cap.name == "test-skill"
        assert cap.source_type == "cli-anything"
        assert "run" in cap.arguments

    def test_parse_skill_md_nonexistent(self):
        assert SKILLParser.parse_skill_md("/nonexistent/SKILL.md") is None

    def test_parse_from_string(self):
        content = """---
name: inline-skill
description: Inline test
---
"""
        cap = SKILLParser.parse_from_string(content, "inline-skill")
        assert cap is not None
        assert cap.name == "inline-skill"

    def test_extract_commands(self):
        body = """
| `analyze <file>` | Analyze |
| `lint <dir>` | Lint |
"""
        commands = SKILLParser._extract_commands_from_tables(body)
        assert "analyze" in commands
        assert "lint" in commands
        assert commands["analyze"]["positional_args"] == ["file"]


class TestCLIRunner:
    def test_run_echo(self):
        runner = CLIRunner()
        result = runner.run(["echo", "hello"], use_json=False)
        assert result.success is True
        assert "hello" in result.stdout

    def test_run_with_json(self):
        runner = CLIRunner()
        result = runner.run(["echo", '{"ok":true}'], use_json=True)
        assert result.success is True

    def test_run_nonexistent_command(self):
        runner = CLIRunner()
        result = runner.run(["nonexistent_command_xyz_12345"])
        assert result.success is False
        assert result.error_type == "not_found"

    def test_run_classify_error(self):
        assert CLIRunner._classify_error("command not found", 127) == "not_found"
        assert CLIRunner._classify_error("permission denied", 126) == "permission_error"
        assert CLIRunner._classify_error("timeout", 1) == "timeout"
        assert CLIRunner._classify_error("generic error", 1) == "execution_error"


class TestCLIAnythingAdapter:
    def test_is_available(self):
        adapter = CLIAnythingAdapter()
        assert isinstance(adapter.is_available(), bool)

    def test_discover(self):
        adapter = CLIAnythingAdapter()
        caps = adapter.discover()
        assert isinstance(caps, list)

    def test_run(self):
        adapter = CLIAnythingAdapter()
        result = adapter.run(["echo", "test"], use_json=False)
        assert result.success is True
        assert "test" in result.stdout
