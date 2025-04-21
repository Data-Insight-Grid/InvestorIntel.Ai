from unittest.mock import MagicMock

# Create mock objects
mock_client = MagicMock()
mock_client.table.return_value.insert.return_value.execute.return_value = {"data": [{"id": "1"}]}

# Create a mock for the module
def create_client(*args, **kwargs):
    return mock_client

def log_gemini_interaction(**kwargs):
    return {"status": "success", "message": "Mock log entry created"}
