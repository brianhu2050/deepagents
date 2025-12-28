import asyncio
import os
from performance_agent.agent import create_performance_agent

async def main():
    """
    Main function to run the performance analysis agent.
    """
    # This would typically come from a config file or environment variable
    model = "claude-3-5-sonnet-20240620"
    assistant_id = "performance-analyzer"

    agent = create_performance_agent(model=model, assistant_id=assistant_id)

    user_request = "Analyze the performance of instance 'i-12345' and generate a report."

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": user_request}]}
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

if __name__ == "__main__":
    asyncio.run(main())
