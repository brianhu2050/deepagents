from unittest.mock import AsyncMock, MagicMock

def create_mock_daytona_sandbox():
    """
    Creates a mock Daytona sandbox for testing purposes.
    """
    mock_sandbox = MagicMock()
    mock_sandbox.id = "mock-daytona-sandbox"

    # Mock the `execute` method to simulate code execution
    def mock_execute(command, timeout=None):
        print(f"Executing in mock Daytona sandbox: {command}")
        # In a real scenario, you'd capture stdout/stderr and return an exit code.
        # For this example, we'll just print the command.
        return MagicMock(exit_code=0, output="Successfully executed")

    mock_sandbox.process.exec.side_effect = mock_execute

    # The DaytonaBackend expects a Daytona sandbox object, not a mock.
    # To get around this, we'll create a mock DaytonaBackend and attach the mock `execute` method to it.
    mock_daytona_backend = MagicMock()
    mock_daytona_backend.id = "mock-daytona-backend"
    mock_daytona_backend.execute = mock_execute
    mock_daytona_backend.awrite = AsyncMock(return_value=MagicMock(files_update={}))

    return mock_daytona_backend
