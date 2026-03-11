"""
Pytest configuration and fixtures for tests.
"""
import sys
from unittest.mock import Mock, MagicMock
import pytest

# Mock modules that have dependency conflicts to allow tests to run
# This is necessary because google-adk and logfire have conflicting
# opentelemetry-sdk version requirements

# Mock logfire
sys.modules['logfire'] = MagicMock()

# Create mock Content class that can be used with isinstance
class MockContent:
    def __init__(self, role='user', parts=None):
        self.role = role
        self.parts = parts or []

class MockPart:
    def __init__(self, text=None, file_data=None, inline_data=None):
        self.text = text
        self.file_data = file_data
        self.inline_data = inline_data

    @staticmethod
    def from_bytes(data, mime_type):
        return MockPart()

class MockFileData:
    def __init__(self, file_uri):
        self.file_uri = file_uri

class MockBlob:
    def __init__(self, data, mime_type):
        self.data = data
        self.mime_type = mime_type

# Create types mock with these classes
types_mock = MagicMock()
types_mock.Content = MockContent
types_mock.Part = MockPart
types_mock.FileData = MockFileData
types_mock.Blob = MockBlob
types_mock.GenerateContentConfig = MagicMock
types_mock.HttpOptions = MagicMock
types_mock.HttpRetryOptions = MagicMock
types_mock.FunctionCall = MagicMock
types_mock.FunctionResponse = MagicMock

# Mock google-adk modules - need to create proper nested mock structure
google_mock = MagicMock()
sys.modules['google'] = google_mock
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = types_mock
sys.modules['google.adk'] = MagicMock()
sys.modules['google.adk.agents'] = MagicMock()
sys.modules['google.adk.runners'] = MagicMock()
sys.modules['google.adk.sessions'] = MagicMock()
sys.modules['google.adk.models'] = MagicMock()
sys.modules['google.adk.events'] = MagicMock()
sys.modules['google.adk.sessions.database_session_service'] = MagicMock()

# Mock src.tools and src.prompts
sys.modules['src.tools'] = MagicMock()
sys.modules['src.prompts'] = MagicMock()
sys.modules['src.prompts.prompt_manager'] = MagicMock()


@pytest.fixture(autouse=True)
def reset_media_buffer_and_jobs():
    """Reset global state before each test"""
    try:
        from src.telegram import bot
        bot.MEDIA_GROUP_BUFFER.clear()
        bot.SCHEDULED_JOBS.clear()
        yield
        bot.MEDIA_GROUP_BUFFER.clear()
        bot.SCHEDULED_JOBS.clear()
    except:
        # If imports fail, just yield without clearing
        yield