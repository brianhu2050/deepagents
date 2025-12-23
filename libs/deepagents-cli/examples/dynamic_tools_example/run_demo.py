"""
This script demonstrates the dynamic tool loading functionality of deepagents.

It configures an agent with SkillsMiddleware and the new ToolLoadingMiddleware,
pointing them to a sample skill that defines a tool in its SKILL.md file.

The agent is then invoked with a prompt that requires the dynamically loaded
tool, proving that the entire workflow is successful.
"""

import asyncio
import os
from pathlib import Path

from typing import Any, Callable, Sequence
from langchain_core.runnables import Runnable
from langchain_core.language_models import LanguageModelInput
from langchain_core.tools import BaseTool
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class FixedGenericFakeChatModel(GenericFakeChatModel):
    """Fixed version of GenericFakeChatModel that properly handles bind_tools."""

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        """Override bind_tools to return self."""
        return self

# Adjust the python path to include the root of the project
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


from deepagents.graph import create_deep_agent
from deepagents_cli.skills.middleware import SkillsMiddleware
from deepagents_cli.skills.tool_middleware import ToolLoadingMiddleware


async def main():
    """Main function to run the demonstration."""
    print("--- Dynamic Tool Loading Demonstration ---")

    # --- 1. Configure paths for the skill ---
    # The skill is located in the `system_info` directory within this example.
    # Note: In a real application, this might point to ~/.deepagents/agent/skills
    skill_dir = Path(__file__).parent / "system_info"
    # The ToolLoadingMiddleware needs to import from the `contrib` folder
    # so we need to ensure deepagents_cli is in the path. We've done that above.

    print(f"Loading skills from: {skill_dir}")
    if not skill_dir.exists() or not (skill_dir / "SKILL.md").exists():
        print(
            "\nError: The example skill directory or SKILL.md does not exist."
        )
        print(
            "Please ensure you are running this script from the correct location."
        )
        return

    # --- 2. Set up the Middleware ---
    # We need both SkillsMiddleware (to load metadata) and ToolLoadingMiddleware (to load tools).
    # The order doesn't strictly matter as `create_deep_agent` handles the logic,
    # but logically SkillsMiddleware comes first.
    skills_middleware = SkillsMiddleware(
        skills_dir=skill_dir, assistant_id="demo_agent"
    )
    tool_loading_middleware = ToolLoadingMiddleware()

    # --- 3. Set up a deterministic Fake LLM ---
    # To make this demo reliable and not require API keys, we'll use a fake model.
    # We will program it to call our dynamically loaded tool `get_current_datetime`.
    fake_model = FixedGenericFakeChatModel(
        messages=iter(
            [
                # First, the model decides to call the tool.
                AIMessage(
                    content="I need to get the current time. I will use the `get_current_datetime` tool.",
                    tool_calls=[
                        {
                            "name": "get_current_datetime",
                            "args": {},
                            "id": "tool_call_123",
                            "type": "tool_call",
                        }
                    ],
                ),
                # After the tool is executed, the model gives the final answer.
                AIMessage(
                    content="I have retrieved the current time.",
                ),
            ]
        )
    )

    print("\n--- 4. Create the Agent ---")
    # We create the agent, passing our middleware. `create_deep_agent` will
    # automatically run the middleware hooks, discover the `get_current_datetime`
    # tool from the skill, and add it to the agent's toolset.
    agent = create_deep_agent(
        model=fake_model,
        middleware=[
            skills_middleware,
            tool_loading_middleware,
        ],
        # We don't need to pass any static tools.
        tools=[],
    )

    print("\n--- 5. Invoke the Agent ---")
    prompt = "What time is it right now?"
    print(f"User Prompt: '{prompt}'")

    result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})

    print("\n--- 6. Analyze the Results ---")
    messages = result.get("messages", [])
    tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]

    if not tool_messages:
        print("\n[FAIL] No tool messages were found in the agent's output.")
        return

    print(f"\nFound {len(tool_messages)} tool call(s) in the output.")
    for i, msg in enumerate(tool_messages):
        print(f"  - Tool Call {i+1}:")
        print(f"    - Name: {msg.name}")
        print(f"    - Content: '{msg.content[:100]}...'") # Print first 100 chars
        print(f"    - Tool Call ID: {msg.tool_call_id}")


    if any(msg.name == "get_current_datetime" for msg in tool_messages):
        print("\n[SUCCESS] The `get_current_datetime` tool was successfully called!")
    else:
        print("\n[FAIL] The expected `get_current_datetime` tool was NOT called.")


if __name__ == "__main__":
    asyncio.run(main())
