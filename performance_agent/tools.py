import json
from langchain_core.tools import tool

@tool
def query_metric(instance_id: str) -> str:
    """
    Queries the performance metrics for a given instance ID.
    """
    # In a real-world scenario, this would query a monitoring system.
    # For this example, we'll return some dummy data.
    print(f"Querying metrics for instance: {instance_id}")
    data = {
        "cpu_usage": [10, 15, 12, 18, 25, 30, 28, 22, 20, 15],
        "memory_usage": [50, 55, 52, 60, 65, 70, 68, 62, 60, 55],
        "timestamps": [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:01:00Z",
            "2024-01-01T00:02:00Z",
            "2024-01-01T00:03:00Z",
            "2024-01-01T00:04:00Z",
            "2024-01-01T00:05:00Z",
            "2024-01-01T00:06:00Z",
            "2024-01-01T00:07:00Z",
            "2024-01-01T00:08:00Z",
            "2024-01-01T00:09:00Z",
        ],
    }
    return json.dumps(data)
