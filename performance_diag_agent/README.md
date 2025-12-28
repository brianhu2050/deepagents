# Performance Diagnosis Agent

This project is a standalone agent application that uses the `deepagents` framework to diagnose and visualize performance metrics.

## Architecture

This agent is built as a standalone application and is not an extension of the `deepagents-cli`. Its architecture is designed to be both modular and robust:

-   **Tools (`tools.py`):** The agent's core capabilities are defined as distinct, asynchronous tools:
    -   `query_metric`: Fetches performance data. To handle potentially large datasets, it saves the data to a file within the sandbox and returns only the file path, preventing context window overflow.
    -   `metric_analysis_visualize`: A "smart" tool that accepts a data file path and a user's natural language request. It uses an LLM to dynamically generate a Python visualization script, which it then executes in the sandbox to produce a chart.

-   **Skills (`skills/diagnostics/SKILL.md`):** The agent's workflow is orchestrated by a `SKILL.md` file. This file provides a step-by-step guide that the agent follows, instructing it to first call `query_metric` and then pass the resulting file path to `metric_analysis_visualize`. This demonstrates how `deepagents` can follow structured, long-term plans.

-   **Skills Middleware (`deepagents_cli.skills.middleware`):** The agent uses the official `SkillsMiddleware` from the `deepagents-cli` package to load and manage skills.

-   **Backend (`DaytonaBackend`):** The agent is configured to use a real `DaytonaBackend`, providing a secure, isolated sandbox for all file operations and for executing the dynamically generated Python code.

## Setup

1.  **Install Dependencies:**

    This project is part of a monorepo. To run it, you must first install the local `deepagents` and `deepagents-cli` packages in editable mode, followed by this project's dependencies.

    ```bash
    pip install -e libs/deepagents
    pip install -e libs/deepagents-cli
    pip install -e .
    ```

2.  **Set API Keys:**

    The agent requires API keys for both Anthropic (for the LLM) and Daytona (for the sandbox). These must be set as environment variables.

    ```bash
    export ANTHROPIC_API_KEY="your-anthropic-api-key"
    export DAYTONA_API_KEY="your-daytona-api-key"
    ```

## Usage

To run the agent, execute the main application script:

```bash
python -m performance_diag_agent.main
```

The agent will then follow the workflow defined in its skill file to perform the end-to-end analysis.
