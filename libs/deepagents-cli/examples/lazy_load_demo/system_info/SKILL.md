---
name: system-info
description: Provides tools to get system information, like the current date and time.
tools:
  - "deepagents_cli.skills.contrib.system.get_current_datetime"
---

# System Information Skill

This skill provides a set of tools for retrieving basic system information.

## Tools

### `get_current_datetime`

- **Description**: Returns the current date and time, formatted as a string.
- **Usage**: Call this tool when you need to know the current time or include a timestamp in your response.
- **Example**: `get_current_datetime()` or `get_current_datetime(format="%Y-%m-%d")`.
