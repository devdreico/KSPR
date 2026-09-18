"""SkillsManager — loads and manages skill bundles for KSPR I."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills" / "gsap-skills"


class SkillBundle:
    """Represents a loaded skill bundle from disk."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        skill_path: str,
        skill_content: str,
        enabled: bool = True,
        metadata: dict | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.version = version
        self.skill_path = skill_path
        self.skill_content = skill_content
        self.enabled = enabled
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "skill_path": self.skill_path,
            "skill_content": self.skill_content,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


class SkillsManager:
    """Manages skill bundle loading and context generation for KSPR I."""

    def __init__(self, skills_dir: str | None = None) -> None:
        self._skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self._bundles: dict[str, SkillBundle] = {}
        self._load_default_bundles()

    def _load_default_bundles(self) -> None:
        """Load all enabled bundles from the skills directory."""
        manifest_path = self._skills_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"Manifest not found: {manifest_path}")
            return

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading manifest: {e}")
            return

        for skill_id, skill_info in manifest.get("skills", {}).items():
            if not skill_info.get("enabled", True):
                continue

            skill_path = self._skills_dir / skill_info["skill_path"]
            if not skill_path.exists():
                logger.warning(f"SKILL.md not found: {skill_path}")
                continue

            try:
                content = skill_path.read_text(encoding="utf-8")
                bundle = SkillBundle(
                    name=skill_info["name"],
                    description=skill_info["description"],
                    version=skill_info.get("version", "0.0.1"),
                    skill_path=str(skill_path),
                    skill_content=content,
                    enabled=True,
                    metadata=skill_info.get("metadata", {}),
                )
                self._bundles[skill_id] = bundle
                logger.info(f"Skill bundle loaded: {skill_id}")
            except Exception as e:
                logger.error(f"Error loading skill {skill_id}: {e}")

        logger.info(f"SkillsManager: {len(self._bundles)} bundles loaded")

    def list_bundles(self) -> list[SkillBundle]:
        return list(self._bundles.values())

    def get_bundle(self, name: str) -> SkillBundle | None:
        return self._bundles.get(name)

    def get_skill_context(self) -> str:
        """Generate concatenated context from all enabled skills for LLM injection."""
        contexts: list[str] = []
        for bundle in self._bundles.values():
            if bundle.enabled:
                contexts.append(
                    f"=== Skill: {bundle.name} ===\n"
                    f"{bundle.skill_content}\n"
                    f"=== End Skill: {bundle.name} ===\n"
                )
        return "\n".join(contexts)

    def enable(self, name: str) -> bool:
        if name in self._bundles:
            self._bundles[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self._bundles:
            self._bundles[name].enabled = False
            return True
        return False

    def reload(self) -> None:
        self._bundles.clear()
        self._load_default_bundles()
