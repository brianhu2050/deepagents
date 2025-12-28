# Performance Analyzer Skill

This skill enables the agent to perform a comprehensive performance analysis of a given instance.

## Workflow

The agent will follow these steps:

1.  **Query Performance Metrics:** The agent will call the `query_metric` tool to generate a large JSON dataset of performance metrics. This dataset will be saved to a file in the `/workspace/` directory, and the tool will return the file path.
2.  **Generate Plotting Script:** The agent will use the `code-generator` sub-agent to generate a Python script that reads the performance data from the JSON file and creates a plot using `matplotlib`. The plot will be saved as `/workspace/performance_chart.png`.
3.  **Save and Execute the Script:** The agent will save the generated script to `/workspace/plotter.py` and then execute it in the Daytona sandbox.
4.  **Verify the Output:** The agent will use the `ls` tool to verify that the `performance_chart.png` file was created.
5.  **Generate the Final Report:** The agent will create a final report at `/workspace/performance_report.md` that summarizes the steps taken and confirms the successful generation of the performance chart.

## Requirements

To use this skill, you must have the following environment variables set:

-   `ANTHROPIC_API_KEY`: Your Anthropic API key.
-   `DAYTONA_API_KEY`: Your Daytona API key.
