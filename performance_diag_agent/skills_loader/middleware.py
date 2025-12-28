"""Middleware for loading and exposing agent skills to the system prompt."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime

from performance_diag_agent.skills_loader.load import SkillMetadata, list_skills


class SkillsState(AgentState):
    """State for the skills middleware."""

    skills_metadata: NotRequired[list[SkillMetadata]]


class SkillsStateUpdate(TypedDict):
    """State update for the skills middleware."""

    skills_metadata: list[SkillMetadata]


SKILLS_SYSTEM_PROMPT = """

## Skills System

You have access to a skills library that provides specialized capabilities and domain knowledge.

**Available Skills:**

{skills_list}

**How to Use Skills (Progressive Disclosure):**

1. **Recognize when a skill applies**: Check if the user's task matches any skill's description.
2. **Read the skill's full instructions**: The skill list above shows the exact path to use with `read_file`.
3. **Follow the skill's instructions**: The `SKILL.md` file contains the step-by-step workflow to follow.
"""


class SkillsMiddleware(AgentMiddleware):
    """Middleware for loading and exposing agent skills."""

    state_schema = SkillsState

    def __init__(self, skills_dir: str | Path) -> None:
        """Initialize the skills middleware."""
        self.skills_dir = Path(skills_dir).expanduser()
        self.system_prompt_template = SKILLS_SYSTEM_PROMPT

    def _format_skills_list(self, skills: list[SkillMetadata]) -> str:
        """Format skills metadata for display in system prompt."""
        if not skills:
            return f"(No skills available in {self.skills_dir}/)"

        lines = [
            f"- **{skill['name']}**: {skill['description']}\n  → Read `{skill['path']}` for full instructions"
            for skill in skills
        ]
        return "\n".join(lines)

    def before_agent(self, state: SkillsState, runtime: Runtime) -> SkillsStateUpdate | None:
        """Load skills metadata before agent execution."""
        skills = list_skills(skills_dir=self.skills_dir)
        return SkillsStateUpdate(skills_metadata=skills)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Inject skills documentation into the system prompt."""
        state = cast("SkillsState", request.state)
        skills_metadata = state.get("skills_metadata", [])
        skills_list = self._format_skills_list(skills_metadata)
        skills_section = self.system_prompt_template.format(skills_list=skills_list)

        system_prompt = (
            f"{request.system_prompt}\n\n{skills_section}"
            if request.system_prompt
            else skills_section
        )

        return await handler(request.override(system_prompt=system_prompt))
