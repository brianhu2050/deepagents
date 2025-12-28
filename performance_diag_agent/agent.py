"""Agent assembly for the performance diagnosis agent."""
import os

from daytona import Daytona, DaytonaConfig
from langchain_anthropic import ChatAnthropic

from deepagents import create_deep_agent
from deepagents.backends.daytona import DaytonaBackend
from performance_diag_agent.middleware import PerformanceDiagMiddleware


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

    # Initialize the custom middleware
    middleware = PerformanceDiagMiddleware(model)

    # Create the deep agent
    agent = create_deep_agent(
        model=model,
        system_prompt="You are a performance diagnosis expert.",
        middleware=[middleware],
        backend=backend,
    )

    return agent
