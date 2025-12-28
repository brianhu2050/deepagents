---
name: "diagnostics"
description: "Diagnoses and visualizes performance metrics for a given instance."
---

# Performance Diagnostics Skill

This skill guides the agent through a workflow to diagnose and visualize performance metrics.

## Workflow

1.  **Query Metrics:**
    *   Call the `query_metric` tool with the `instance_id` provided by the user.
    *   This tool will save the performance data to a JSON file in the `/workspace/` directory and return the path to this file.

2.  **Visualize Metrics:**
    *   Call the `metric_analysis_visualize` tool.
    *   Use the file path returned from `query_metric` as the `data_path` parameter.
    *   Use the user's original request as the `request` parameter.
    *   This tool will generate and execute a Python script to create a chart and save it to `/workspace/performance_chart.png`.

3.  **Confirm Completion:**
    *   Use the `ls` tool to verify that `/workspace/performance_chart.png` was created.
    *   Inform the user that the analysis is complete and the chart has been generated.
