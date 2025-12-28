"""Tools for the performance diagnosis agent, correctly defined using StructuredTool."""
import json
import uuid

from langchain.tools import ToolRuntime
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool

from deepagents.backends.sandbox import SandboxBackendProtocol

# --- Tool Logic Functions ---
# These are the raw functions that contain the tool's logic.
# They accept `runtime: ToolRuntime` as the first argument, which is injected
# by the `StructuredTool.from_function` wrapper.

async def _async_query_metric(runtime: ToolRuntime, instance_id: str) -> str:
    """The asynchronous implementation for the query_metric tool."""
    print(f"Querying metrics for instance: {instance_id}")
    data = {
        "cpu_usage": [10, 15, 12, 18, 25, 30, 28, 22, 20, 15] * 100,
        "memory_usage": [50, 55, 52, 60, 65, 70, 68, 62, 60, 55] * 100,
        "timestamps": [f"2024-01-01T00:{i:02d}:00Z" for i in range(10)] * 100,
    }

    file_path = f"/workspace/metrics_{uuid.uuid4()}.json"
    # Access the backend via the runtime object
    await runtime.backend.awrite(file_path, json.dumps(data, indent=2))

    return f"Performance data saved to {file_path}"

async def _async_metric_analysis_visualize(
    runtime: ToolRuntime, data_path: str, request: str, model: ChatAnthropic
) -> str:
    """The asynchronous implementation for the metric_analysis_visualize tool."""
    backend = runtime.backend
    if not isinstance(backend, SandboxBackendProtocol):
        return "Error: This tool requires a sandbox backend for code generation and execution."

    # 1. Generate Python script using the provided LLM model
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a Python expert specializing in data visualization. "
                "Your task is to write a Python script that reads a JSON file "
                "from a given path and generates a plot using matplotlib based on "
                "the user's request. The script should save the plot to a file. "
                "Make sure to include all necessary imports, such as `json` and `matplotlib.pyplot`.",
            ),
            (
                "user",
                f"Data file path: {data_path}\n"
                f"Request: {request}\n"
                "Save the output chart to '/workspace/performance_chart.png'",
            ),
        ]
    )
    response = await model.ainvoke(prompt)
    # The response content might include markdown code fences, so we need to extract the raw code.
    script_code = response.content.strip().replace("```python", "").replace("```", "").strip()


    # 2. Save the generated script to a file
    script_path = f"/workspace/visualizer_{uuid.uuid4()}.py"
    await backend.awrite(script_path, script_code)

    # 3. Execute the script in the sandbox
    exec_result = await backend.aexecute(f"python {script_path}")
    if exec_result.exit_code != 0:
        return f"Error executing visualization script: {exec_result.output}"

    return "Successfully generated visualization at /workspace/performance_chart.png"


# --- Tool Factory ---
# This function creates and configures the tools, returning them as a list.
# This is a clean pattern for managing tool dependencies, like the LLM model.

def get_performance_diag_tools(model: ChatAnthropic) -> list[StructuredTool]:
    """
    Creates and returns the list of tools for the performance diagnosis agent.
    """
    # Create the query_metric tool
    query_metric_tool = StructuredTool.from_function(
        name="query_metric",
        description="Queries performance metrics for a given instance ID and saves the data to a file.",
        coroutine=_async_query_metric,
    )

    # Create the metric_analysis_visualize tool.
    # We use a closure (a nested function) to capture the `model` variable,
    # so the tool's execution logic has access to it without changing the
    # signature that the agent's tool-calling mechanism expects.
    async def visualize_tool_wrapper(runtime: ToolRuntime, data_path: str, request: str) -> str:
        return await _async_metric_analysis_visualize(runtime, data_path, request, model)

    metric_analysis_visualize_tool = StructuredTool.from_function(
        name="metric_analysis_visualize",
        description="Generates and executes a Python script to visualize performance data based on a user's request.",
        coroutine=visualize_tool_wrapper,
    )

    return [query_metric_tool, metric_analysis_visualize_tool]
