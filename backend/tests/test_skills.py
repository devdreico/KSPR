from kspr_engine.skills import SkillBundle, SkillsManager


class TestSkillBundle:
    def test_create(self):
        bundle = SkillBundle(
            name="test",
            description="Test bundle",
            version="1.0.0",
            skill_path="/path/SKILL.md",
            skill_content="# Test",
            enabled=True,
        )
        assert bundle.name == "test"
        assert bundle.enabled is True

    def test_to_dict(self):
        bundle = SkillBundle(
            name="test",
            description="Test",
            version="1.0.0",
            skill_path="/path",
            skill_content="content",
        )
        d = bundle.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"

    def test_metadata_default(self):
        bundle = SkillBundle(
            name="test", description="", version="1.0",
            skill_path="", skill_content="",
        )
        assert bundle.metadata == {}


class TestSkillsManager:
    def test_load_default_bundles(self):
        sm = SkillsManager()
        bundles = sm.list_bundles()
        assert len(bundles) == 3

    def test_get_bundle(self):
        sm = SkillsManager()
        bundle = sm.get_bundle("cli-anything-default")
        assert bundle is not None
        assert bundle.name == "cli-anything-default"

    def test_get_bundle_nonexistent(self):
        sm = SkillsManager()
        assert sm.get_bundle("nonexistent") is None

    def test_get_skill_context(self):
        sm = SkillsManager()
        context = sm.get_skill_context()
        assert len(context) > 0
        assert "cli-anything-default" in context

    def test_enable_disable(self):
        sm = SkillsManager()
        assert sm.disable("cli-anything-default") is True
        bundle = sm.get_bundle("cli-anything-default")
        assert bundle.enabled is False
        assert sm.enable("cli-anything-default") is True
        assert bundle.enabled is True

    def test_enable_nonexistent(self):
        sm = SkillsManager()
        assert sm.enable("nonexistent") is False

    def test_reload(self):
        sm = SkillsManager()
        sm.disable("cli-anything-default")
        sm.reload()
        bundle = sm.get_bundle("cli-anything-default")
        assert bundle.enabled is True
