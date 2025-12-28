"""Middleware for performance analysis tools."""
import json
import uuid

from langchain.agents.middleware.types import AgentMiddleware
from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool


def _query_metric_tool_generator() -> StructuredTool:
    """Generate the query_metric tool."""

    def _query_metric(runtime: ToolRuntime, instance_id: str) -> str:
        """Queries performance metrics and saves them to a file."""
        # In a real-world scenario, this would query a monitoring system.
        # For this example, we'll generate some dummy data.
        print(f"Querying metrics for instance: {instance_id}")
        data = {
            "cpu_usage": [10, 15, 12, 18, 25, 30, 28, 22, 20, 15] * 1000,
            "memory_usage": [50, 55, 52, 60, 65, 70, 68, 62, 60, 55] * 1000,
            "timestamps": [
                f"2024-01-01T00:{i:02d}:00Z" for i in range(10)
            ] * 1000,
        }

        # Save the data to a file in the workspace
        file_path = f"/workspace/metrics_{uuid.uuid4()}.json"
        runtime.backend.write(file_path, json.dumps(data, indent=2))

        return f"Performance data saved to {file_path}"

    async def _aquery_metric(runtime: ToolRuntime, instance_id: str) -> str:
        """Async queries performance metrics and saves them to a file."""
        # In a real-world scenario, this would query a monitoring system.
        # For this example, we'll generate some dummy data.
        print(f"Querying metrics for instance: {instance_id}")
        data = {
            "cpu_usage": [10, 15, 12, 18, 25, 30, 28, 22, 20, 15] * 1000,
            "memory_usage": [50, 55, 52, 60, 65, 70, 68, 62, 60, 55] * 1000,
            "timestamps": [
                f"2024-01-01T00:{i:02d}:00Z" for i in range(10)
            ] * 1000,
        }

        # Save the data to a file in the workspace
        file_path = f"/workspace/metrics_{uuid.uuid4()}.json"
        await runtime.backend.awrite(file_path, json.dumps(data, indent=2))

        return f"Performance data saved to {file_path}"

    return StructuredTool.from_function(
        name="query_metric",
        description="Queries performance metrics for a given instance ID and saves the data to a file.",
        func=_query_metric,
        coroutine=_aquery_metric,
    )


class PerformanceAnalysisMiddleware(AgentMiddleware):
    """Middleware for performance analysis tools."""

    def __init__(self) -> None:
        """Initialize the middleware."""
        self.tools = [_query_metric_tool_generator()]
