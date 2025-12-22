"""Example contrib tools for demonstration."""
from datetime import datetime
from langchain_core.tools import tool

@tool
def get_current_datetime(
    format: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """Returns the current date and time, formatted as a string.

    Args:
        format: The format string for the datetime object.
                Defaults to "%Y-%m-%d %H:%M:%S".
    """
    return datetime.now().strftime(format)
