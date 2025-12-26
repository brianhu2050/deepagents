# Data+AI Agent Implementation Guide

This document provides a developer-focused, step-by-step guide on how to configure and extend `deepagents` to create a powerful Data+AI agent. This agent can execute analysis code in a secure sandbox while accessing large datasets from the local filesystem.

## 1. Goal: A Hybrid Filesystem Agent

Our goal is to create an agent that operates with a hybrid filesystem:
- **`/workspace`**: Handled by a secure, remote **SandboxBackend**. This is where code execution, temporary file creation, and analysis results will live.
- **`/data`**: Handled by a **FilesystemBackend**. This directory is mapped to a persistent folder on the local machine (`~/deepagents_data`), allowing the agent to work with large, persistent datasets without loading them into the sandbox.

---

## 2. Step 1: Configuring `CompositeBackend`

The key to the hybrid filesystem is the `CompositeBackend`. We will configure it within the core agent creation logic of the `deepagents-cli`.

**File to Modify**: `libs/deepagents-cli/deepagents_cli/agent.py`

**Function to Modify**: `create_cli_agent`

Locate the `REMOTE SANDBOX MODE` section within this function and apply the following changes:

```python
# In libs/deepagents-cli/deepagents_cli/agent.py, inside create_cli_agent()

# ... (other code)
    else:
        # ========== REMOTE SANDBOX MODE ==========

        # 1. Initialize the local filesystem backend for persistent data
        #    This maps the agent's /data/ directory to a real folder in the user's home.
        data_dir = Path.home() / "deepagents_data"
        data_dir.mkdir(exist_ok=True)
        filesystem_backend = FilesystemBackend(base_dir=str(data_dir))

        # 2. Configure CompositeBackend to route traffic
        #    - Default: All paths go to the sandbox.
        #    - Route: Paths starting with /data/ go to the local filesystem backend.
        composite_backend = CompositeBackend(
            default=sandbox,
            routes={
                "/data/": filesystem_backend,
            },
        )

        # ... (rest of the function)
```

**Result**: With this change, any tool using the backend (like `ls`, `read_file`, `write_file`) will now correctly route file operations based on the path.

---

## 3. Step 2: Implementing the `DataAnalysisMiddleware`

To give our agent the ability to execute Python code, we will create a new middleware that provides a `run_python_script` tool. This is preferable to a standalone "skill" because middleware can be properly initialized with access to the agent's core components, like the `backend`.

### 3.1. Create the Middleware File

**New File**: `libs/deepagents-cli/deepagents_cli/data_analysis.py`

**Content**:
```python
"""Middleware for providing data analysis tools to the agent."""

from deepagents.backends.protocol import BackendProtocol, SandboxBackendProtocol
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain.tools import tool
from langgraph.pregel import PregelI, ToolNode
from langgraph.runtime import Runtime

class DataAnalysisMiddleware(AgentMiddleware):
    """
    This middleware provides a `run_python_script` tool for data analysis.
    It requires a sandbox-capable backend to execute code.
    """

    def __init__(self, backend: BackendProtocol):
        self.backend = backend

    @property
    def tools(self) -> list:
        @tool
        def run_python_script(script: str) -> str:
            """
            Executes a Python script in the sandbox for data analysis.
            The script should be self-contained. It can read data from the '/data/'
            directory and should write results to '/workspace/results/'. Always
            print a final summary or confirmation to standard output upon completion.
            """
            if not isinstance(self.backend, SandboxBackendProtocol):
                return "Error: A sandbox environment is required for code execution."

            script_path = "/workspace/temp_analysis_script.py"
            # Use the composite backend to write the script into the sandbox
            write_result = self.backend.write(script_path, script)
            if write_result.error:
                return f"Error writing temporary script to sandbox: {write_result.error}"

            # Execute the script in the sandbox
            execute_response = self.backend.execute(f"python {script_path}")

            # Note: A production implementation should add cleanup for the temp script.

            return execute_response.output

        return [run_python_script]

    def on_enter(
        self,
        *,
        state: AgentState,
        runtime: Runtime,
        graph: "PregelI",
        tool_node: ToolNode,
    ) -> AgentState:
        return state
```

### 3.2. Integrate the Middleware

Now, let's add our new middleware to the agent's middleware stack.

**File to Modify**: `libs/deepagents-cli/deepagents_cli/agent.py`

**Function to Modify**: `create_cli_agent`

```python
# In libs/deepagents-cli/deepagents_cli/agent.py

# Add the new import at the top of the file
from deepagents_cli.data_analysis import DataAnalysisMiddleware

# ... inside create_cli_agent()

    # Build middleware stack based on enabled features
    agent_middleware = []

    # ...

    # In REMOTE SANDBOX MODE section, after setting up composite_backend
    else:
        # ... (composite_backend setup as above)

        # Add memory middleware
        if enable_memory:
            agent_middleware.append(
                AgentMemoryMiddleware(settings=settings, assistant_id=assistant_id)
            )

        # Add our new DataAnalysisMiddleware
        agent_middleware.append(DataAnalysisMiddleware(backend=composite_backend))

        # Add skills middleware
        if enable_skills:
        # ...
```

**Result**: The agent now has a powerful `run_python_script` tool available whenever it's running in sandbox mode.

---

## 4. Step 3: Guiding the Agent to Be an Orchestrator

The final piece is not code, but instruction. We must guide the LLM to use its new tools in a structured, methodical way. This is achieved by crafting a detailed `agent.md` file, which acts as the agent's core behavioral instruction set.

### 4.1. Create a Data Analyst Agent Profile

A user would create a new agent profile (e.g., named `data_analyst`) and edit the `agent.md` file for it.

**Example File**: `~/.deepagents/data_analyst/agent.md`

**Content**:
```markdown
# Role: Data Analysis Orchestrator

You are an expert Data Analysis agent. Your primary goal is to solve complex data-related problems by planning and executing a sequence of tasks.

## Your Workflow

When presented with a data analysis request (e.g., "Find the cause of last night's API errors"), you must follow this structured workflow:

1.  **Clarify & Plan**:
    *   First, understand the user's goal. If the request is ambiguous, ask clarifying questions.
    *   Second, formulate a high-level, step-by-step plan. Write this plan down for the user to see using your `write_todos` tool. **Always ask for the user's approval on the plan before proceeding.**
    *   Example Plan:
        1.  List files in `/data/logs/` to identify relevant log files.
        2.  Read the content of the identified log file to understand its structure.
        3.  Use `run_python_script` to analyze the log file, counting error types and correlating them with timestamps.
        4.  Summarize the findings and present the results.

2.  **Execute Step-by-Step**:
    *   Execute the plan one step at a time, choosing the best tool for each step.
    *   Use `run_python_script` for all data processing and analysis.
    *   **Input Data**: Read from `/data/`.
    *   **Output Results**: Write artifacts to `/workspace/results/`.

3.  **Summarize & Conclude**:
    *   After execution, provide a clear summary of your findings, referencing any generated artifacts.

## Guiding Principles
*   **Think Step-by-Step**: Decompose complex problems.
*   **Be Methodical**: Follow your plan systematically.
*   **Be Transparent**: Communicate your plan and results clearly.
```

---

## 5. End-to-End Example Workflow

1.  **User places data**: A user places `production_logs.csv` into their local `~/deepagents_data/` directory.
2.  **User starts agent**: `deepagents --agent data_analyst`
3.  **User makes request**: "Please analyze `production_logs.csv` and find the most common error codes."
4.  **Agent Plans**: The agent, following its `agent.md` instructions, creates a todo list:
    *   [ ] Read the head of `/data/production_logs.csv` to understand columns.
    *   [ ] Use `run_python_script` to load the CSV with pandas, count error codes, and save the counts to `/workspace/results/error_counts.csv`.
    *   [ ] Read the result file and present it to the user.
    *   The agent asks: "Does this plan look good?"
5.  **User Approves**: "Yes, proceed."
6.  **Agent Executes**:
    *   Calls `read_file("/data/production_logs.csv", limit=10)`. `CompositeBackend` routes this to `FilesystemBackend`.
    *   Calls `run_python_script` with a pandas script. `DataAnalysisMiddleware` handles the call. `CompositeBackend` writes the script to `/workspace/` (sandbox) and then executes it in the sandbox. The script reads from `/data/` (local) and writes to `/workspace/` (sandbox).
    *   Calls `read_file("/workspace/results/error_counts.csv")`. `CompositeBackend` routes this to `SandboxBackend`.
7.  **Agent Reports**: The agent displays the contents of the result file and provides a summary.

This completes the implementation, creating a robust, practical, and powerful Data+AI agent.
