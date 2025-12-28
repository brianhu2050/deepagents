import os
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent
from deepagents.backends.composite import CompositeBackend
from performance_agent.middleware.skills import SkillsMiddleware

from performance_agent.sandbox import create_mock_daytona_sandbox
from performance_agent.subagents import code_generator_subagent
from performance_agent.tools import query_metric

def create_performance_agent(model: str, assistant_id: str):
    """
    Assembles the main performance analysis agent.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    chat_model = ChatAnthropic(model_name=model)
    sandbox = create_mock_daytona_sandbox()
    composite_backend = CompositeBackend(default=sandbox, routes={})

    skills_middleware = SkillsMiddleware(
        skills_dir="performance_agent/skills",
        assistant_id=assistant_id,
    )

    agent = create_deep_agent(
        model=chat_model,
        system_prompt="You are a performance analysis expert.",
        tools=[query_metric],
        backend=composite_backend,
        middleware=[skills_middleware],
        subagents=[code_generator_subagent],
    )

    return agent
