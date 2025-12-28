"""Main entry point for the performance diagnosis agent."""
import asyncio
import os

from performance_diag_agent.agent import create_performance_diag_agent


async def main():
    """Main function to run the agent."""
    agent = create_performance_diag_agent(
        model_name="claude-3-5-sonnet-20240620",
        assistant_id="performance-diag-agent",
    )

    user_request = (
        "Diagnose the performance of instance 'i-12345' and create a visualization of CPU and memory usage."
    )

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": user_request}]}
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()


if __name__ == "__main__":
    # For this example to run, you must have the following environment variables set:
    # export ANTHROPIC_API_KEY="your-anthropic-api-key"
    # export DAYTONA_API_KEY="your-daytona-api-key"
    asyncio.run(main())
