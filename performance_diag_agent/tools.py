"""Tools for the performance diagnosis agent."""
import json
import uuid

from langchain.tools import ToolRuntime
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from deepagents.backends.sandbox import SandboxBackendProtocol


@tool
async def query_metric(runtime: ToolRuntime, instance_id: str) -> str:
    """Queries performance metrics and saves them to a file."""
    print(f"Querying metrics for instance: {instance_id}")
    data = {
        "cpu_usage": [10, 15, 12, 18, 25, 30, 28, 22, 20, 15] * 100,
        "memory_usage": [50, 55, 52, 60, 65, 70, 68, 62, 60, 55] * 100,
        "timestamps": [f"2024-01-01T00:{i:02d}:00Z" for i in range(10)] * 100,
    }

    file_path = f"/workspace/metrics_{uuid.uuid4()}.json"
    await runtime.backend.awrite(file_path, json.dumps(data, indent=2))

    return f"Performance data saved to {file_path}"


@tool
async def metric_analysis_visualize(
    runtime: ToolRuntime, data_path: str, request: str
) -> str:
    """Generates and executes a Python script to visualize performance data."""
    backend = runtime.backend
    if not isinstance(backend, SandboxBackendProtocol):
        return "Error: This tool requires a sandbox backend for code generation and execution."

    model = ChatAnthropic(model_name="claude-3-5-sonnet-20240620")
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
    script_code = response.content

    script_path = f"/workspace/visualizer_{uuid.uuid4()}.py"
    await backend.awrite(script_path, script_code)

    exec_result = await backend.aexecute(f"python {script_path}")
    if exec_result.exit_code != 0:
        return f"Error executing visualization script: {exec_result.output}"

    return "Successfully generated visualization at /workspace/performance_chart.png"
