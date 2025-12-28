# Performance Analysis Agent

This project demonstrates how to build a `deepagent` that can analyze the performance of a given instance.

## Features

-   **Skills-based workflow:** The agent's workflow is defined in a `skill.md` file, which makes it easy to modify and extend.
-   **Sub-agent for code generation:** The agent uses a sub-agent to generate Python code for plotting performance data.
-   **Daytona sandbox integration:** The agent executes the generated code in a Daytona sandbox, providing an isolated and secure environment.
-   **End-to-end workflow:** The agent can perform the entire performance analysis workflow, from querying metrics to generating a final report.

## Setup

1.  **Install the `deepagents` and `deepagents-cli` packages:**

    ```bash
    pip install -e libs/deepagents
    pip install -e libs/deepagents-cli
    ```

2.  **Set the `ANTHROPIC_API_KEY` environment variable:**

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"
    ```

3.  **Run the main application:**

    ```bash
    python -m performance_agent.main
    ```
