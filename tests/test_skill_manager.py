"""Tests for SkillManager."""

from pathlib import Path

import pytest

from utils.skill_manager import SkillManager


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    return tmp_path / "skills"


@pytest.fixture
def mgr(skills_dir: Path) -> SkillManager:
    return SkillManager(skills_dir=skills_dir)


def test_list_empty(mgr: SkillManager) -> None:
    assert mgr.list_skills() == []


def test_create_and_list(mgr: SkillManager) -> None:
    mgr.create_skill("my-skill", "A test skill", "# Content\nHello.")
    skills = mgr.list_skills()
    assert len(skills) == 1
    assert skills[0]["name"] == "my-skill"
    assert skills[0]["description"] == "A test skill"


def test_create_duplicate_raises(mgr: SkillManager) -> None:
    mgr.create_skill("dup", "desc", "body")
    with pytest.raises(FileExistsError):
        mgr.create_skill("dup", "desc2", "body2")


def test_create_invalid_slug_raises(mgr: SkillManager) -> None:
    with pytest.raises(ValueError):
        mgr.create_skill("Invalid Name!", "desc", "body")


def test_read_skill(mgr: SkillManager) -> None:
    mgr.create_skill("read-me", "desc", "# Hello")
    content = mgr.read_skill("read-me")
    assert "Hello" in content


def test_read_missing_raises(mgr: SkillManager) -> None:
    with pytest.raises(FileNotFoundError):
        mgr.read_skill("nope")


def test_update_skill(mgr: SkillManager) -> None:
    mgr.create_skill("upd", "desc", "# Old")
    mgr.update_skill("upd", "# New content")
    content = mgr.read_skill("upd")
    assert "New content" in content


def test_update_skill_with_description(mgr: SkillManager) -> None:
    mgr.create_skill("with-desc", "old description", "# Body")
    mgr.update_skill("with-desc", "# Updated body", description="new description")
    content = mgr.read_skill("with-desc")
    assert "new description" in content
    assert "Updated body" in content


def test_update_missing_raises(mgr: SkillManager) -> None:
    with pytest.raises(FileNotFoundError):
        mgr.update_skill("ghost", "new content")


def test_delete_skill(mgr: SkillManager) -> None:
    mgr.create_skill("del-me", "desc", "body")
    mgr.delete_skill("del-me")
    assert mgr.list_skills() == []


def test_delete_missing_raises(mgr: SkillManager) -> None:
    with pytest.raises(FileNotFoundError):
        mgr.delete_skill("nothing")


def test_delete_core_raises(mgr: SkillManager) -> None:
    with pytest.raises(PermissionError):
        mgr.delete_skill("trading-bot-overview")


def test_apply_skill(mgr: SkillManager) -> None:
    mgr.create_skill("apply-me", "desc", "Hello $ARGUMENTS!")
    rendered = mgr.apply_skill("apply-me", "World")
    assert rendered == "---\nname: apply-me\ndescription: desc\n---\n\nHello World!\n"


def test_configurable_skills_dir(tmp_path: Path) -> None:
    custom = tmp_path / "custom_skills"
    m = SkillManager(skills_dir=custom)
    m.create_skill("test", "desc", "body")
    assert (custom / "test" / "SKILL.md").is_file()
