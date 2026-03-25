"""Skill CRUD manager — manage .claude/skills as first-class objects.

Provides create, read, update, delete, and apply operations on skill
folders stored in `.claude/skills/`.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)

# Skills that cannot be deleted via the API
_CORE_SKILLS = frozenset({
    "trading-bot-overview",
    "coding-standards",
    "implement-agent",
    "add-strategy",
})

_SLUG_RE = re.compile(r"^[a-z][a-z0-9\-]*$")


class SkillManager:
    """CRUD manager for `.claude/skills/` skill folders."""

    SKILLS_DIR = Path(".claude/skills")

    def __init__(self, db: "Database | None" = None, skills_dir: "Path | None" = None) -> None:
        self._db = db
        if skills_dir is not None:
            self.SKILLS_DIR = skills_dir

    # ── helpers ───────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        """Write a DB log entry if a db handle was provided."""
        if self._db is not None:
            try:
                self._db.log_agent_event("skill_manager", "info", message)
            except Exception:
                logger.debug("skill_manager DB log failed", exc_info=True)

    @staticmethod
    def _parse_frontmatter(text: str) -> dict[str, str]:
        """Extract YAML-ish frontmatter key/value pairs from SKILL.md."""
        meta: dict[str, str] = {}
        if not text.startswith("---"):
            return meta
        end = text.find("---", 3)
        if end == -1:
            return meta
        block = text[3:end].strip()
        for line in block.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()
        return meta

    # ── public API ────────────────────────────────────────────────────────

    def list_skills(self) -> list[dict]:
        """Return a list of skill metadata dicts."""
        result: list[dict] = []
        if not self.SKILLS_DIR.is_dir():
            return result
        for child in sorted(self.SKILLS_DIR.iterdir()):
            if not child.is_dir():
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.is_file():
                continue
            content = skill_file.read_text(encoding="utf-8")
            meta = self._parse_frontmatter(content)
            result.append({
                "name": meta.get("name", child.name),
                "description": meta.get("description", ""),
                "location": str(skill_file),
                "user_invocable": meta.get("user-invocable", "true").lower() != "false",
            })
        return result

    def read_skill(self, name: str) -> str:
        """Return the full markdown content of a skill by name."""
        skill_file = self.SKILLS_DIR / name / "SKILL.md"
        if not skill_file.is_file():
            raise FileNotFoundError(f"Skill '{name}' not found")
        return skill_file.read_text(encoding="utf-8")

    def create_skill(self, name: str, description: str, content: str) -> Path:
        """Create a new skill folder + SKILL.md. Raise if already exists."""
        if not _SLUG_RE.match(name):
            raise ValueError(
                f"Skill name must be lowercase with hyphens only, got: '{name}'"
            )
        skill_dir = self.SKILLS_DIR / name
        if skill_dir.exists():
            raise FileExistsError(f"Skill '{name}' already exists")

        skill_dir.mkdir(parents=True, exist_ok=False)
        skill_file = skill_dir / "SKILL.md"

        # Build SKILL.md with frontmatter
        md = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"---\n\n"
            f"{content}\n"
        )
        skill_file.write_text(md, encoding="utf-8")

        self._log(f"Created skill '{name}'")
        logger.info("Skill created: %s", name)
        return skill_file

    def update_skill(self, name: str, content: str, description: str | None = None) -> None:
        """Overwrite the content of an existing skill. Raise if not found.

        If *description* is provided, the frontmatter description field is
        updated (or added) while preserving all other frontmatter keys.
        """
        skill_file = self.SKILLS_DIR / name / "SKILL.md"
        if not skill_file.is_file():
            raise FileNotFoundError(f"Skill '{name}' not found")

        if description is not None:
            # Re-build frontmatter with updated description
            existing = skill_file.read_text(encoding="utf-8")
            meta = self._parse_frontmatter(existing)
            meta["description"] = description
            # Strip existing frontmatter from the supplied content if present
            body = content
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    body = content[end + 3:].lstrip("\n")
            fm_lines = "\n".join(f"{k}: {v}" for k, v in meta.items())
            content = f"---\n{fm_lines}\n---\n\n{body}\n"

        skill_file.write_text(content, encoding="utf-8")
        self._log(f"Updated skill '{name}'")
        logger.info("Skill updated: %s", name)

    def delete_skill(self, name: str) -> None:
        """Delete a skill folder and its SKILL.md. Raise if not found."""
        if name in _CORE_SKILLS:
            raise PermissionError(
                f"Cannot delete core skill '{name}' "
                f"(protected: {', '.join(sorted(_CORE_SKILLS))})"
            )
        skill_dir = self.SKILLS_DIR / name
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")
        shutil.rmtree(skill_dir)

        self._log(f"Deleted skill '{name}'")
        logger.info("Skill deleted: %s", name)

    def apply_skill(self, name: str, argument: str = "") -> str:
        """Render a skill's content with $ARGUMENTS replaced.

        Also logs the application to the database.
        """
        content = self.read_skill(name)
        rendered = content.replace("$ARGUMENTS", argument)

        self._log(f"Applied skill '{name}' with argument='{argument}'")
        logger.info("Skill applied: %s (arg='%s')", name, argument)
        return rendered
