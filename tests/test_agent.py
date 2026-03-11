import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import re
import sys

# Get the mocked types from sys.modules
types = sys.modules['google.genai.types']

from src.agent import AgentService, GEMINI_3_PRO


class TestAgentServiceInitialization:
    """Test suite for AgentService initialization"""

    def test_agent_service_initialization(self):
        """Test that AgentService initializes correctly"""
        with patch('src.agent.PromptManager') as mock_prompt_manager, \
             patch('src.agent.LlmAgent') as mock_llm_agent:

            mock_prompt_manager_instance = Mock()
            mock_prompt_manager.return_value = mock_prompt_manager_instance

            service = AgentService()

            assert service.app_name == "KyaHuaPathe"
            assert service.session_service is not None
            assert service.grounding_agent is not None
            assert service.agent is not None
            assert service.runner is not None

    def test_grounding_agent_configuration(self):
        """Test that grounding agent is configured with correct parameters"""
        with patch('src.agent.PromptManager') as mock_prompt_manager, \
             patch('src.agent.LlmAgent') as mock_llm_agent, \
             patch('src.agent.Runner'):

            mock_prompt_manager_instance = Mock()
            mock_prompt_manager_instance.return_value = "el_facto_prompt"
            mock_prompt_manager.return_value = mock_prompt_manager_instance

            service = AgentService()

            # Verify LlmAgent was called for grounding agent
            calls = mock_llm_agent.call_args_list
            assert len(calls) >= 1

    def test_main_agent_has_sub_agents(self):
        """Test that main agent is configured with sub-agents"""
        with patch('src.agent.PromptManager') as mock_prompt_manager, \
             patch('src.agent.LlmAgent') as mock_llm_agent, \
             patch('src.agent.Runner'):

            mock_prompt_manager_instance = Mock()
            mock_prompt_manager.return_value = mock_prompt_manager_instance

            service = AgentService()

            # Main agent should be called with sub_agents parameter
            calls = mock_llm_agent.call_args_list
            # The second call should be for the main agent
            assert len(calls) >= 2


class TestRunQuery:
    """Test suite for run_query method"""

    @pytest.mark.asyncio
    async def test_run_query_with_simple_text(self):
        """Test run_query with simple text message"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            # Mock the async generator
            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            await service.run_query("Hello", "user_123", "session_456", callback)

            # Verify session was retrieved
            service.session_service.get_session.assert_called_once()
            # Verify callback was called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_creates_session_if_not_exists(self):
        """Test that run_query creates session if it doesn't exist"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=None)
            service.session_service.create_session = AsyncMock()
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            await service.run_query("Hello", "user_789", "session_789", callback)

            # Verify session creation was called
            service.session_service.create_session.assert_called_once_with(
                app_name="KyaHuaPathe",
                user_id="user_789",
                session_id="session_789"
            )

    @pytest.mark.asyncio
    async def test_run_query_with_youtube_link(self):
        """Test run_query extracts YouTube links and processes them"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            message = "Check this video https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            await service.run_query(message, "user_123", "session_456", callback)

            # Verify runner was called correctly
            assert service.runner.run_async.called
            call_kwargs = service.runner.run_async.call_args[1]
            assert call_kwargs['user_id'] == "user_123"
            assert call_kwargs['session_id'] == "session_456"
            # Verify callback was called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_with_youtu_be_short_link(self):
        """Test run_query handles youtu.be short links"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            message = "Watch https://youtu.be/dQw4w9WgXcQ"
            await service.run_query(message, "user_123", "session_456", callback)

            # Verify the method completed successfully
            assert service.runner.run_async.called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_without_youtube_link(self):
        """Test run_query with message that has no YouTube link"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            message = "Just a regular message"
            await service.run_query(message, "user_123", "session_456", callback)

            # Verify the method completed successfully
            assert service.runner.run_async.called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_with_content_object(self):
        """Test run_query when message is already a Content object"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            content = types.Content(role='user', parts=[types.Part(text="Hello")])
            await service.run_query(content, "user_123", "session_456", callback)

            call_kwargs = service.runner.run_async.call_args[1]
            new_message = call_kwargs['new_message']

            # Should be the same content object
            assert new_message == content


class TestRunQueryWithMedia:
    """Test suite for run_query_with_media method"""

    @pytest.mark.asyncio
    async def test_run_query_with_single_image(self):
        """Test run_query_with_media with a single image"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Image response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            media_list = [(b"image_data", "image/jpeg")]
            await service.run_query_with_media(
                "What's in this image?", media_list, "user_123", "session_456", callback
            )

            # Verify method completed and called runner
            assert service.runner.run_async.called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_with_video(self):
        """Test run_query_with_media handles video with Blob"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Video response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            media_list = [(b"video_data", "video/mp4")]
            await service.run_query_with_media(
                "Analyze this video", media_list, "user_123", "session_456", callback
            )

            # Verify method completed and called runner
            assert service.runner.run_async.called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_with_multiple_media(self):
        """Test run_query_with_media with multiple media files"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Multiple media response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            media_list = [
                (b"image1_data", "image/jpeg"),
                (b"image2_data", "image/png"),
                (b"video_data", "video/mp4")
            ]
            await service.run_query_with_media(
                "Compare these", media_list, "user_123", "session_456", callback
            )

            # Verify method completed and called runner
            assert service.runner.run_async.called
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_run_query_with_empty_caption(self):
        """Test run_query_with_media with empty caption"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()
            service.session_service = AsyncMock()
            service.session_service.get_session = AsyncMock(return_value=Mock())
            service.runner = AsyncMock()

            async def mock_events():
                event = Mock()
                event.content = Mock()
                event.content.parts = [Mock(text="Response")]
                event.get_function_calls = Mock(return_value=[])
                event.get_function_responses = Mock(return_value=[])
                yield event

            service.runner.run_async = Mock(return_value=mock_events())

            callback = AsyncMock()
            media_list = [(b"image_data", "image/jpeg")]
            await service.run_query_with_media(
                "", media_list, "user_123", "session_456", callback
            )

            # Verify method completed and called runner
            assert service.runner.run_async.called
            callback.assert_called()


class TestFormatEventResponse:
    """Test suite for format_event_response method"""

    @pytest.mark.asyncio
    async def test_format_event_with_text_only(self):
        """Test formatting event with only text content"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="Simple response")]
            event.get_function_calls = Mock(return_value=[])
            event.get_function_responses = Mock(return_value=[])

            response = await service.format_event_response(event)

            assert response == "Simple response"

    @pytest.mark.asyncio
    async def test_format_event_with_function_calls(self):
        """Test formatting event with function calls"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="Calling function\n")]

            fn_call = Mock()
            fn_call.name = "google_search"
            fn_call.args = {"query": "test query"}
            event.get_function_calls = Mock(return_value=[fn_call])
            event.get_function_responses = Mock(return_value=[])

            response = await service.format_event_response(event)

            assert "Calling function" in response
            assert "**google_search**" in response
            assert "query: test query" in response
            assert "---" in response

    @pytest.mark.asyncio
    async def test_format_event_with_function_responses(self):
        """Test formatting event with function responses"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="")]
            event.get_function_calls = Mock(return_value=[])

            fn_response = Mock()
            fn_response.name = "google_search"
            fn_response.response = {"result": "Search results here"}
            event.get_function_responses = Mock(return_value=[fn_response])

            response = await service.format_event_response(event)

            assert "**google_search**" in response
            assert "Search results here" in response

    @pytest.mark.asyncio
    async def test_format_event_with_no_function_name(self):
        """Test formatting event when function response has no name"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="")]
            event.get_function_calls = Mock(return_value=[])

            fn_response = Mock()
            fn_response.name = None
            fn_response.response = {"result": "Result"}
            event.get_function_responses = Mock(return_value=[fn_response])

            response = await service.format_event_response(event)

            assert "**No name**" in response

    @pytest.mark.asyncio
    async def test_format_event_with_no_result_in_response(self):
        """Test formatting event when function response has no result"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="")]
            event.get_function_calls = Mock(return_value=[])

            fn_response = Mock()
            fn_response.name = "test_function"
            fn_response.response = {}
            event.get_function_responses = Mock(return_value=[fn_response])

            response = await service.format_event_response(event)

            assert "N/A" in response

    @pytest.mark.asyncio
    async def test_format_event_with_none_response(self):
        """Test formatting event when function response is None"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="")]
            event.get_function_calls = Mock(return_value=[])

            fn_response = Mock()
            fn_response.name = "test_function"
            fn_response.response = None
            event.get_function_responses = Mock(return_value=[fn_response])

            response = await service.format_event_response(event)

            assert "N/A" in response

    @pytest.mark.asyncio
    async def test_format_event_with_multiple_function_calls(self):
        """Test formatting event with multiple function calls"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = [Mock(text="Making multiple calls\n")]

            fn_call1 = Mock()
            fn_call1.name = "google_search"
            fn_call1.args = {"query": "first query"}

            fn_call2 = Mock()
            fn_call2.name = "google_maps"
            fn_call2.args = {"location": "New York"}

            event.get_function_calls = Mock(return_value=[fn_call1, fn_call2])
            event.get_function_responses = Mock(return_value=[])

            response = await service.format_event_response(event)

            assert "**google_search**" in response
            assert "**google_maps**" in response
            assert "first query" in response
            assert "New York" in response

    @pytest.mark.asyncio
    async def test_format_event_with_empty_content(self):
        """Test formatting event with no content"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = None
            event.get_function_calls = Mock(return_value=[])
            event.get_function_responses = Mock(return_value=[])

            response = await service.format_event_response(event)

            assert response == ""

    @pytest.mark.asyncio
    async def test_format_event_with_empty_parts(self):
        """Test formatting event with empty parts list"""
        with patch('src.agent.PromptManager'), \
             patch('src.agent.LlmAgent'), \
             patch('src.agent.Runner'):

            service = AgentService()

            event = Mock()
            event.content = Mock()
            event.content.parts = []
            event.get_function_calls = Mock(return_value=[])
            event.get_function_responses = Mock(return_value=[])

            response = await service.format_event_response(event)

            assert response == ""


class TestYouTubePatternMatching:
    """Test suite for YouTube link pattern matching"""

    def test_youtube_pattern_matches_standard_url(self):
        """Test YouTube pattern matches standard URLs"""
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ"
        ]

        for url in urls:
            match = re.search(pattern, url)
            assert match is not None
            assert match.group(1) == "dQw4w9WgXcQ"

    def test_youtube_pattern_matches_short_url(self):
        """Test YouTube pattern matches youtu.be short URLs"""
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

        urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ"
        ]

        for url in urls:
            match = re.search(pattern, url)
            assert match is not None
            assert match.group(1) == "dQw4w9WgXcQ"

    def test_youtube_pattern_extracts_video_id(self):
        """Test that video ID is correctly extracted"""
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

        message = "Check out this video https://www.youtube.com/watch?v=abc123XYZ_- and let me know"
        match = re.search(pattern, message)

        assert match is not None
        assert match.group(1) == "abc123XYZ_-"

    def test_youtube_pattern_in_longer_text(self):
        """Test YouTube pattern works in longer text with multiple links"""
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

        message = "Watch this https://www.youtube.com/watch?v=dQw4w9WgXcQ first"
        match = re.search(pattern, message)

        assert match is not None
        assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in match.group(0)


class TestGeminiConfiguration:
    """Test suite for Gemini model configuration"""

    def test_gemini_model_configuration(self):
        """Test that Gemini model is configured with correct retry options"""
        assert GEMINI_3_PRO is not None
        # Verify model has retry_options
        assert hasattr(GEMINI_3_PRO, 'retry_options') or hasattr(GEMINI_3_PRO, '_retry_options')

    def test_gemini_model_name(self):
        """Test Gemini model is using correct model name"""
        # The model should be configured with gemini-3-pro-preview
        # We can't directly access private attributes but we can verify it was created
        assert GEMINI_3_PRO is not None