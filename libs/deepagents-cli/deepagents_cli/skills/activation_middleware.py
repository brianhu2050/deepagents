"""Middleware for activating skill tools at runtime when a skill is read."""

import yaml
from collections.abc import Callable
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from langchain.agents.middleware.types import AgentMiddleware, AgentState, ToolCall, ToolResponse
from langchain_core.tools import BaseTool

from deepagents_cli.skills.load import SkillMetadata
from deepagents_cli.skills.tool_loader import load_tools_from_skills


class SkillActivationState(AgentState):
    """State for the skill activation middleware."""

    active_skill_tools: NotRequired[dict[str, BaseTool]]
    """A mapping of tool names to tool objects that have been activated."""


class SkillActivationStateUpdate(TypedDict):
    """State update for the skill activation middleware."""

    active_skill_tools: dict[str, BaseTool]
    """The updated mapping of activated skill tools."""


class SkillActivationMiddleware(AgentMiddleware):
    """
    Activates tools defined in a SKILL.md file when that file is read.

    This middleware implements true progressive disclosure for tools. Tools
    associated with a skill only become available to the agent *after* the
    agent has explicitly read the skill's documentation using `read_file`.
    """

    state_schema = SkillActivationState

    def wrap_tool_call(
        self,
        call: ToolCall,
        handler: Callable[[ToolCall], ToolResponse],
    ) -> ToolResponse:
        """
        Intercepts tool calls to `read_file`.

        If a `SKILL.md` file is being read, it parses the frontmatter,
        loads the associated tools, and adds them to the agent's state.
        """
        # First, let the original tool call proceed.
        response = handler(call)

        # Now, check if it was a successful `read_file` on a `SKILL.md`.
        if (
            call.tool == "read_file"
            and isinstance(call.args.get("filepath"), str)
            and call.args["filepath"].endswith("SKILL.md")
            and not response.is_error
        ):
            try:
                # The response.content is the full content of the file.
                # We need to parse the YAML frontmatter from it.
                content = response.content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) > 2:
                        frontmatter = yaml.safe_load(parts[1])
                        if isinstance(frontmatter, dict):
                            # We treat the frontmatter as a SkillMetadata object
                            # and pass it to our existing tool loader.
                            # We need to add the 'path' for the loader to work.
                            frontmatter["path"] = call.args["filepath"]
                            newly_loaded_tools = load_tools_from_skills([frontmatter])

                            if newly_loaded_tools:
                                # Get the current active tools from the response's state.
                                current_tools = response.state.get("active_skill_tools", {})
                                for tool in newly_loaded_tools:
                                    current_tools[tool.name] = tool

                                # Update the state on the response.
                                response.state["active_skill_tools"] = current_tools
            except (yaml.YAMLError, KeyError) as e:
                # If parsing fails, we don't do anything.
                # In a real app, you might want to log this.
                print(f"Could not parse frontmatter from {call.args['filepath']}: {e}")

        return response
