"""Custom tool execution logic for handling dynamically activated skill tools."""

from typing import List, Dict
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_executor import ToolExecutor

from langchain.agents.middleware.types import AgentState


def create_dynamic_tool_node(static_tools: List[BaseTool]):
    """
    Creates a custom tool node that merges static tools with dynamically
    activated tools from the agent's state before execution.

    Args:
        static_tools: A list of tools that are always available.

    Returns:
        A function that serves as a dynamic tool node for a LangGraph agent.
    """
    static_tool_map = {tool.name: tool for tool in static_tools}
    tool_executor = ToolExecutor(static_tools)

    def dynamic_tool_node(state: AgentState) -> dict:
        """
        The custom tool node. It reads `active_skill_tools` from the state,
        merges them with the static tools, and then executes the tool call.
        """
        # Get the most recent tool calls from the last AIMessage.
        last_message = state.get("messages", [])[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        # Get active skill tools from the state.
        active_skill_tools: Dict[str, BaseTool] = state.get("active_skill_tools", {})

        # Create a temporary, combined tool executor for this specific call.
        # This ensures that only the tools active at this moment are available.
        combined_tools = {**static_tool_map, **active_skill_tools}

        # We need to create a new ToolExecutor instance if skill tools are present.
        # Otherwise, we can use the pre-initialized one.
        current_executor = tool_executor
        if active_skill_tools:
            current_executor = ToolExecutor(list(combined_tools.values()))

        # Execute the tool calls.
        tool_messages = []
        for tool_call in last_message.tool_calls:
            try:
                output = current_executor.invoke(tool_call)
                tool_messages.append(
                    ToolMessage(content=str(output), tool_call_id=tool_call["id"])
                )
            except Exception as e:
                tool_messages.append(
                    ToolMessage(
                        content=f"Error executing tool {tool_call['name']}: {e}",
                        tool_call_id=tool_call["id"],
                    )
                )

        return {"messages": tool_messages}

    return dynamic_tool_node
