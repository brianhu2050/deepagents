"""Deepagents come with planning, filesystem, and subagents."""

from collections.abc import Callable, Sequence
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt.tool_executor import ToolExecutor
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from typing import Annotated, Literal
from langchain_core.runnables import chain
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents.middleware import AgentState
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    InterruptOnConfig,
    TodoListMiddleware,
    apply_middleware,
)
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ResponseFormat
from langchain.agents.tool_calling_agent import should_continue
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from deepagents.backends.protocol import BackendFactory, BackendProtocol
from deepagents.dynamic_tools import create_dynamic_tool_node
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import (
    CompiledSubAgent,
    SubAgent,
    SubAgentMiddleware,
)

BASE_AGENT_PROMPT = "In order to complete the objective that the user asks of you, you have access to a number of standard tools."


def get_default_model() -> ChatAnthropic:
    """Get the default model for deep agents.

    Returns:
        ChatAnthropic instance configured with Claude Sonnet 4.
    """
    return ChatAnthropic(
        model_name="claude-sonnet-4-5-20250929",
        max_tokens=20000,
    )


def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph:
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    seven file and execution tools: ls, read_file, write_file, edit_file, glob, grep, execute,
    and a tool to call subagents.

    The execute tool allows running shell commands if the backend implements SandboxBackendProtocol.
    For non-sandbox backends, the execute tool will return an error message.

    Args:
        model: The model to use. Defaults to Claude Sonnet 4.
        tools: The tools the agent should have access to.
        system_prompt: The additional instructions the agent should have. Will go in
            the system prompt.
        middleware: Additional middleware to apply after standard middleware.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the
                  sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `model` (either a LanguageModelLike instance or dict
                  settings)
                - (optional) `middleware` (list of AgentMiddleware)
        response_format: A structured output response format to use for the agent.
        context_schema: The schema of the deep agent.
        checkpointer: Optional checkpointer for persisting agent state between runs.
        store: Optional store for persistent storage (required if backend uses StoreBackend).
        backend: Optional backend for file storage and execution. Pass either a Backend instance
            or a callable factory like `lambda rt: StateBackend(rt)`. For execution support,
            use a backend that implements SandboxBackendProtocol.
        interrupt_on: Optional Dict[str, bool | InterruptOnConfig] mapping tool names to
            interrupt configs.
        debug: Whether to enable debug mode. Passed through to create_agent.
        name: The name of the agent. Passed through to create_agent.
        cache: The cache to use for the agent. Passed through to create_agent.

    Returns:
        A configured deep agent.
    """
    if model is None:
        model = get_default_model()

    if (
        model.profile is not None
        and isinstance(model.profile, dict)
        and "max_input_tokens" in model.profile
        and isinstance(model.profile["max_input_tokens"], int)
    ):
        trigger = ("fraction", 0.85)
        keep = ("fraction", 0.10)
    else:
        trigger = ("tokens", 170000)
        keep = ("messages", 6)

    deepagent_middleware = [
        TodoListMiddleware(),
        FilesystemMiddleware(backend=backend),
        SubAgentMiddleware(
            default_model=model,
            default_tools=tools,
            subagents=subagents if subagents is not None else [],
            default_middleware=[
                TodoListMiddleware(),
                FilesystemMiddleware(backend=backend),
                SummarizationMiddleware(
                    model=model,
                    trigger=trigger,
                    keep=keep,
                    trim_tokens_to_summarize=None,
                ),
                AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
                PatchToolCallsMiddleware(),
            ],
            default_interrupt_on=interrupt_on,
            general_purpose_agent=True,
        ),
        SummarizationMiddleware(
            model=model,
            trigger=trigger,
            keep=keep,
            trim_tokens_to_summarize=None,
        ),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
        PatchToolCallsMiddleware(),
    ]
    if middleware:
        deepagent_middleware.extend(middleware)
    if interrupt_on is not None:
        deepagent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    # Determine if we need to use the dynamic tool node.
    use_dynamic_tools = any(
        "SkillActivationMiddleware" in m.__class__.__name__ for m in middleware
    )

    # Manually build the graph to allow for custom tool node injection.
    # This logic is adapted from langchain.agents.create_agent.
    if context_schema:
        workflow = StateGraph(context_schema)
    else:
        workflow = StateGraph(AgentState)

    # Create the agent node
    agent_runnable = apply_middleware(
        model,
        *deepagent_middleware,
        system_prompt=(
            system_prompt + "\n\n" + BASE_AGENT_PROMPT
            if system_prompt
            else BASE_AGENT_PROMPT
        ),
        response_format=response_format,
        name=name,
    )

    async def agent_node(state: AgentState, config: RunnableConfig):
        """Runs the agent."""
        agent_outcome = await agent_runnable.ainvoke(state, config)
        parser = ToolsAgentOutputParser()
        parsed_outcome = parser.invoke(agent_outcome)
        if isinstance(parsed_outcome, list):
            return {"messages": [AIMessage(tool_calls=parsed_outcome)]}
        else:
            return {"messages": [AIMessage(content=parsed_outcome.return_values["output"])]}

    workflow.add_node("agent", agent_node)

    # Create the tool node
    if use_dynamic_tools:
        tool_node = create_dynamic_tool_node(tools or [])
    else:
        tool_node = ToolNode(tools or [])
    workflow.add_node("tools", tool_node)

    # Define edges
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "agent")
    workflow.add_edge(START, "agent")

    # Compile the graph
    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"],
        debug=debug,
        cache=cache,
    )
    return graph.with_config({"recursion_limit": 1000})
