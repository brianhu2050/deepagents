---
description: "Analyzes the performance of a given instance by querying metrics, generating a plot, and creating a report."
---
# Performance Analysis Skill

This skill enables the agent to analyze the performance of a given instance.

## Workflow

1.  **Gather Performance Data:**
    -   Use the `query_metric` tool with the provided `instance_id` to get the performance data.

2.  **Generate Performance Chart:**
    -   Use the `task` tool to invoke the `code-generator` sub-agent.
    -   The sub-agent's task is to write a Python script that:
        -   Parses the JSON data from `query_metric`.
        -   Uses a library like `matplotlib` to create a plot of CPU and memory usage over time.
        -   Saves the plot to a file named `performance_chart.png`.

3.  **Execute the Script:**
    -   Use the `execute` tool to run the generated Python script in the Daytona sandbox.

4.  **Generate Report:**
    -   Summarize the findings in a `performance_report.md` file.
    -   Include the `performance_chart.png` in the report.
