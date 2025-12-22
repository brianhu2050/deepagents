"""Middleware for dynamically loading tools from skill definitions."""

import importlib
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, NotRequired, TypedDict

from langchain_core.tools import BaseTool
from langgraph.prebuilt.agent_executor import create_agent_executor
from langgraph.prebuilt.chat_agent_executor import (
    create_chat_agent_executor,
)
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.graph.state import StateGraph

from deepagents.backends.protocol import SandboxBackend
from deepagents.middleware.types import (
    AgentInterrupt,
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from deepagents.graph import create_deep_agent

from deepagents_cli.skills.load import SkillMetadata
from deepagents_cli.skills.middleware import SkillsState


class ToolsState(AgentState):
    """State for the skills middleware."""

    skill_tools: NotRequired[list[BaseTool]]
    """List of tools loaded from skills."""


class ToolsStateUpdate(TypedDict):
    """State update for the skills middleware."""

    skill_tools: list[BaseTool]
    """List of tools loaded from skills."""


def load_tools_from_skills(skills: list[SkillMetadata]) -> list[BaseTool]:
    """Dynamically load tools from a list of skill metadata objects.

    Args:
        skills: A list of skill metadata dictionaries.

    Returns:
        A list of instantiated tool objects.
    """
    loaded_tools = []
    for skill in skills:
        tool_imports = skill.get("tools", [])
        if not isinstance(tool_imports, list):
            # We could log a warning here in a real implementation
            continue

        for import_str in tool_imports:
            # Basic security measure: only allow imports from a trusted namespace.
            # In a real-world scenario, this should be more robust.
            if not import_str.startswith("deepagents_cli.skills.contrib."):
                print(f"Skipping potentially insecure tool import: {import_str}")
                continue
            try:
                module_path, tool_name = import_str.rsplit(".", 1)
                module = importlib.import_module(module_path)
                tool_class_or_func = getattr(module, tool_name)

                # Check if it's a class (needs instantiation) or a function
                if isinstance(tool_class_or_func, type) and issubclass(
                    tool_class_or_func, BaseTool
                ):
                    # It's a class, instantiate it
                    tool_instance = tool_class_or_func()
                    loaded_tools.append(tool_instance)
                elif callable(tool_class_or_func) and not isinstance(
                    tool_class_or_func, type
                ):
                    # It's a function, assume it's already a tool or can be decorated
                    # For simplicity, we'll assume it's a @tool decorated function
                    loaded_tools.append(tool_class_or_func)

            except (ImportError, AttributeError, ValueError) as e:
                # In a real app, you'd want to log this error
                print(f"Error loading tool '{import_str}': {e}")
                continue
    return loaded_tools


class ToolLoadingMiddleware(AgentMiddleware):
    """Dynamically loads tools based on skill definitions.

    This middleware should run *after* SkillsMiddleware, as it depends on
    the `skills_metadata` being present in the agent state.

    It reads the `tools` key from the SKILL.md frontmatter, dynamically
    imports and instantiates the tools, and adds them to the agent's
    state.

    NOTE: For these tools to be *executable* by the agent, the agent creation
    process (e.g., in `create_deep_agent`) must be modified to:
    1. Run the `before_agent` hook of this middleware.
    2. Read the `skill_tools` from the resulting state.
    3. Merge these dynamic tools with the static tools before compiling
       the agent graph.
    """

    state_schema = ToolsState

    def before_agent(self, state: ToolsState, runtime: Any) -> ToolsStateUpdate | None:
        """Load tools from skills metadata before agent execution."""
        # This middleware must run after SkillsMiddleware.
        skills_metadata = state.get("skills_metadata", [])
        if not skills_metadata:
            return None

        skill_tools = load_tools_from_skills(skills_metadata)
        if not skill_tools:
            return None

        return ToolsStateUpdate(skill_tools=skill_tools)

    # `wrap_graph_creation` is not suitable for injecting tools that depend on
    # state, as it runs before the state is available. The integration must
    # happen at the agent factory level.
