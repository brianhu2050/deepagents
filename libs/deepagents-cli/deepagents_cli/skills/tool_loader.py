"""Logic for loading tools from skill metadata."""

import importlib
from typing import Any

from langchain_core.tools import BaseTool

from deepagents_cli.skills.load import SkillMetadata


def load_tools_from_skills(skills: list[SkillMetadata]) -> list[BaseTool]:
    """
    Dynamically load tools from a list of skill metadata objects.

    Args:
        skills: A list of skill metadata dictionaries.

    Returns:
        A list of instantiated tool objects.
    """
    loaded_tools = []
    for skill in skills:
        tool_imports = skill.get("tools", [])
        if not isinstance(tool_imports, list):
            continue

        for import_str in tool_imports:
            # Basic security measure: only allow imports from a trusted namespace.
            if not import_str.startswith("deepagents_cli.skills.contrib."):
                print(f"Skipping potentially insecure tool import: {import_str}")
                continue
            try:
                module_path, tool_name = import_str.rsplit(".", 1)
                module = importlib.import_module(module_path)
                tool_class_or_func = getattr(module, tool_name)

                if isinstance(tool_class_or_func, type) and issubclass(
                    tool_class_or_func, BaseTool
                ):
                    tool_instance = tool_class_or_func()
                    loaded_tools.append(tool_instance)
                elif callable(tool_class_or_func) and not isinstance(
                    tool_class_or_func, type
                ):
                    loaded_tools.append(tool_class_or_func)

            except (ImportError, AttributeError, ValueError) as e:
                print(f"Error loading tool '{import_str}': {e}")
                continue
    return loaded_tools
