"""
This script demonstrates the "lazy loading" of tools from skills.

It showcases the SkillActivationMiddleware, where tools defined in a SKILL.md
only become available *after* the agent has explicitly read that file.

The demonstration flow is as follows:
1. Attempt to use a tool that is not yet available -> Fails.
2. Instruct the agent to read the SKILL.md file that defines the tool.
3. Attempt to use the tool again -> Succeeds.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Sequence

# Adjust the python path to include the root of the project
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from langchain.agents.middleware.types import AgentState
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, tool

from deepagents.graph import create_deep_agent
from deepagents_cli.skills.activation_middleware import SkillActivationMiddleware
from deepagents_cli.skills.middleware import SkillsMiddleware


class FixedGenericFakeChatModel(GenericFakeChatModel):
    """Fixed version of GenericFakeChatModel that properly handles bind_tools."""
    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self


async def main():
    """Main function to run the demonstration."""
    print("--- Lazy Loading of Skill Tools Demonstration ---")

    # --- 1. Configure paths and middleware ---
    skill_dir = Path(__file__).parent / "system_info"
    # The FilesystemMiddleware needs a backend. For this demo, we don't need
    # a real filesystem, but the middleware requires the tool to exist.
    @tool
    def read_file(filepath: str) -> str:
        """Reads the content of a file."""
        try:
            with open(filepath, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    skill_activation_middleware = SkillActivationMiddleware()

    # --- 2. Set up a Fake LLM with a sequence of responses ---
    # This model will guide the agent through the 3-step demo process.
    fake_model = FixedGenericFakeChatModel(
        messages=iter(
            [
                # Step 1: Attempt to call the tool (it should fail).
                AIMessage(
                    content="I will try to get the time.",
                    tool_calls=[{"name": "get_current_datetime", "args": {}, "id": "call_1"}],
                ),
                # Step 2: Read the SKILL.md file.
                AIMessage(
                    content="That failed. I should read the skill documentation first.",
                    tool_calls=[{"name": "read_file", "args": {"filepath": str(skill_dir / "SKILL.md")}, "id": "call_2"}],
                ),
                # Step 3: Attempt to call the tool again (it should succeed).
                AIMessage(
                    content="Now that I've read the skill, I'll try again.",
                    tool_calls=[{"name": "get_current_datetime", "args": {}, "id": "call_3"}],
                ),
                AIMessage(content="Done."),
            ]
        )
    )

    # --- 3. Create the Agent ---
    agent = create_deep_agent(
        model=fake_model,
        middleware=[skill_activation_middleware],
        tools=[read_file],  # Only the `read_file` tool is available at the start.
    )

    # --- 4. Run the full flow ---
    print("\n--- Running Agent Flow ---")
    initial_state = {"messages": [HumanMessage(content="Follow the demo steps.")]}

    # We use astream_events to inspect the state at each step.
    final_state = None
    async for event in agent.astream_events(initial_state, version="v1"):
        if event["event"] == "on_end":
            final_state = event["data"]["output"]

    # --- 5. Analyze the final state ---
    print("\n--- Analyzing Results ---")
    messages = final_state.get("messages", [])
    tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]

    call_1 = next((msg for msg in tool_messages if msg.tool_call_id == "call_1"), None)
    call_2 = next((msg for msg in tool_messages if msg.tool_call_id == "call_2"), None)
    call_3 = next((msg for msg in tool_messages if msg.tool_call_id == "call_3"), None)

    print("\nStep 1: First attempt to call `get_current_datetime`")
    if call_1 and "is not a valid tool" in call_1.content:
        print("[SUCCESS] Tool call failed as expected.")
    else:
        print("[FAIL] Tool call should have failed but didn't, or was not found.")

    print("\nStep 2: Reading the SKILL.md file")
    if call_2 and "Error" not in call_2.content:
        print("[SUCCESS] `read_file` was called successfully.")
    else:
        print("[FAIL] `read_file` was not called or failed.")

    print("\nStep 3: Second attempt to call `get_current_datetime`")
    if call_3 and "is not a valid tool" not in call_3.content:
        # A successful call in this test environment will return the tool's output,
        # which is the current date.
        print(f"[SUCCESS] Tool call succeeded as expected. Output: '{call_3.content}'")
    else:
        print("[FAIL] Tool call should have succeeded but failed, or was not found.")

if __name__ == "__main__":
    asyncio.run(main())
