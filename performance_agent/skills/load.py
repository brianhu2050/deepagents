"""Skill loading and parsing utilities."""

from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import yaml
try:
    from langchain_core.utils.yaml import yaml_safe_load
except ImportError:
    from yaml import safe_load as yaml_safe_load


class SkillMetadata(TypedDict):
    """Represents metadata for a single skill."""

    name: str
    """Skill name (from directory name)."""
    description: str
    """Skill description (from SKILL.md frontmatter)."""
    path: str
    """Absolute path to the SKILL.md file."""
    source: Literal["user", "project"]
    """Whether the skill is from the user or project directory."""
    error: NotRequired[str]
    """Error message if skill loading failed."""


def _parse_skill_frontmatter(skill_file: Path) -> tuple[dict, str]:
    """Extract YAML frontmatter from a SKILL.md file.

    Args:
        skill_file: Path to the SKILL.md file.

    Returns:
        A tuple of (metadata, content_after_frontmatter).
    """
    content = skill_file.read_text()
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content  # Not valid frontmatter

    frontmatter_str, _, body = parts
    frontmatter = yaml_safe_load(frontmatter_str) or {}
    return frontmatter, body


def _load_skill(skill_dir: Path, source: Literal["user", "project"]) -> SkillMetadata:
    """Load metadata for a single skill from its directory.

    Args:
        skill_dir: The directory containing the skill.
        source: The source of the skill ('user' or 'project').

    Returns:
        SkillMetadata dictionary.
    """
    skill_file = skill_dir / "SKILL.md"
    skill_name = skill_dir.name

    if not skill_file.exists():
        return {
            "name": skill_name,
            "description": "SKILL.md not found",
            "path": str(skill_file),
            "source": source,
            "error": "SKILL.md not found",
        }

    try:
        frontmatter, _ = _parse_skill_frontmatter(skill_file)
        description = frontmatter.get("description", "No description provided")
        return {
            "name": skill_name,
            "description": description,
            "path": str(skill_file),
            "source": source,
        }
    except yaml.YAMLError as e:
        return {
            "name": skill_name,
            "description": f"Error parsing SKILL.md: {e}",
            "path": str(skill_file),
            "source": source,
            "error": f"YAML parsing error: {e}",
        }


def list_skills(
    *,
    user_skills_dir: Path | str,
    project_skills_dir: Path | str | None = None,
) -> list[SkillMetadata]:
    """List available skills from user and project directories.

    Project skills with the same name as a user skill will override it.

    Args:
        user_skills_dir: Path to the user-level skills directory.
        project_skills_dir: Optional path to the project-level skills directory.

    Returns:
        A list of SkillMetadata dictionaries, with project skills overriding
        user skills.
    """
    user_dir = Path(user_skills_dir)
    project_dir = Path(project_skills_dir) if project_skills_dir else None

    # Load skills from both sources
    user_skills = (
        [_load_skill(d, "user") for d in user_dir.iterdir() if d.is_dir()]
        if user_dir.exists()
        else []
    )
    project_skills = (
        [_load_skill(d, "project") for d in project_dir.iterdir() if d.is_dir()]
        if project_dir and project_dir.exists()
        else []
    )

    # Create a dictionary to handle overrides
    skills_map = {skill["name"]: skill for skill in user_skills}
    skills_map.update({skill["name"]: skill for skill in project_skills})

    # Convert back to a sorted list
    return sorted(skills_map.values(), key=lambda s: s["name"])
