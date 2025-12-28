# Performance Diagnosis Agent

This project provides a standalone agent for performance data diagnosis and analysis, built on the `deepagents` framework.

## Architecture

The agent is designed with a simple yet powerful architecture:

-   **Standalone Application:** This is a self-contained project that uses `deepagents` as a library. It is not an extension of the `deepagents-cli`.
-   **Custom Middleware:** The core logic is implemented in a custom `PerformanceDiagMiddleware`, which provides two key tools:
    -   `query_metric`: This tool generates mock performance data, saves it to a file within the Daytona sandbox, and returns the file path. This approach is designed to handle large datasets efficiently without overloading the agent's context window.
    -   `metric_analysis_visualize`: This "smart" tool accepts a data file path and a natural language request for a visualization. It uses an LLM to generate a Python script, which it then executes in the sandbox to produce a chart.
-   **Daytona Backend:** The agent is configured to use a real `DaytonaBackend`, which provides a secure and isolated environment for file storage and code execution.

## Setup

1.  **Install Dependencies:**

    ```bash
    pip install -e .
    ```

2.  **Set API Keys:**

    You must have `ANTHROPIC_API_KEY` and `DAYTONA_API_KEY` environment variables set. You can either set them in your shell profile or directly in `performance_diag_agent/main.py`.

    ```bash
    export ANTHROPIC_API_KEY="your-anthropic-api-key"
    export DAYTONA_API_KEY="your-daytona-api-key"
    ```

## Usage

To run the agent, simply execute the `main.py` script:

```bash
python -m performance_diag_agent.main
```

The agent will then perform the following steps:

1.  Query the performance metrics for the specified instance.
2.  Generate a Python script to visualize the CPU and memory usage.
3.  Execute the script in the Daytona sandbox to create a `performance_chart.png` file.
4.  Output a message confirming the successful generation of the visualization.
