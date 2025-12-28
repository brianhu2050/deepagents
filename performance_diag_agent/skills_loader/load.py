"""Skill loading and parsing utilities."""
from pathlib import Path
from typing import Literal, TypedDict

import yaml
from langchain_core.utils.yaml import yaml_safe_load


class SkillMetadata(TypedDict):
    """Represents metadata for a single skill."""
    name: str
    description: str
    path: str
    source: Literal["user", "project"]


def _parse_skill_frontmatter(skill_file: Path) -> tuple[dict, str]:
    """Extract YAML frontmatter from a SKILL.md file."""
    content = skill_file.read_text()
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_str, _, body = parts
    frontmatter = yaml_safe_load(frontmatter_str) or {}
    return frontmatter, body


def _load_skill(skill_dir: Path) -> SkillMetadata:
    """Load metadata for a single skill."""
    skill_file = skill_dir / "SKILL.md"
    skill_name = skill_dir.name

    if not skill_file.exists():
        return {
            "name": skill_name,
            "description": "SKILL.md not found",
            "path": str(skill_file),
            "source": "user",
        }

    try:
        frontmatter, _ = _parse_skill_frontmatter(skill_file)
        description = frontmatter.get("description", "No description provided")
        return {
            "name": skill_name,
            "description": description,
            "path": str(skill_file),
            "source": "user",
        }
    except yaml.YAMLError as e:
        return {
            "name": skill_name,
            "description": f"Error parsing SKILL.md: {e}",
            "path": str(skill_file),
            "source": "user",
        }


def list_skills(skills_dir: Path | str) -> list[SkillMetadata]:
    """List available skills from a directory."""
    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return []

    skills = [_load_skill(d) for d in skills_dir.iterdir() if d.is_dir()]
    return sorted(skills, key=lambda s: s["name"])
