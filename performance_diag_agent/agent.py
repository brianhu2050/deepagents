"""Agent assembly for the performance diagnosis agent."""
import os

from daytona import Daytona, DaytonaConfig
from langchain_anthropic import ChatAnthropic

from deepagents import create_deep_agent
from deepagents.backends.daytona import DaytonaBackend
from performance_diag_agent.skills_loader.middleware import SkillsMiddleware
from performance_diag_agent.tools import get_performance_diag_tools


def create_performance_diag_agent(model_name: str, assistant_id: str):
    """Assembles the performance diagnosis agent."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    if not os.environ.get("DAYTONA_API_KEY"):
        raise ValueError("DAYTONA_API_KEY environment variable not set")

    # Initialize the LLM
    model = ChatAnthropic(model_name=model_name)

    # Initialize the Daytona backend
    daytona_client = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    daytona_sandbox = daytona_client.create()
    backend = DaytonaBackend(daytona_sandbox)

    # Initialize the SkillsMiddleware
    skills_middleware = SkillsMiddleware(skills_dir="performance_diag_agent/skills")

    # Get the list of tools, passing the model to the factory
    tools = get_performance_diag_tools(model)

    # Create the deep agent
    agent = create_deep_agent(
        model=model,
        system_prompt="You are a performance diagnosis expert.",
        tools=tools,
        middleware=[skills_middleware],
        backend=backend,
    )

    return agent
