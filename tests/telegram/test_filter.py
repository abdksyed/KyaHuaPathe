import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from src.telegram.filter import handle_input_media, SUPPORTED_MIME_TYPES


class TestHandleInputMedia:
    """Test suite for handle_input_media function"""

    @pytest.mark.asyncio
    async def test_handle_single_photo(self):
        """Test handling a single photo message"""
        # Create mock message with photo
        message = Mock()
        message.caption = "Test photo caption"
        message.media_group_id = None

        # Mock photo attachment (PhotoSize is a list in Telegram)
        # PhotoSize doesn't have mime_type attribute
        photo_size = Mock(spec=['file_id', 'file_unique_id', 'get_file'])
        photo_size.file_id = "photo_123"
        photo_size.file_unique_id = "unique_123"
        message.effective_attachment = [photo_size]

        # Mock file object
        file_obj = AsyncMock()
        file_obj.file_path = "photos/photo_123.jpg"
        photo_size.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["mime_type"] == "image/jpeg"
        assert result["file_name"] == "photo_123.jpg"
        assert result["caption"] == "Test photo caption"
        assert result["media_group_id"] is None
        assert result["file_obj"] == file_obj

    @pytest.mark.asyncio
    async def test_handle_multiple_photo_sizes(self):
        """Test handling photo with multiple sizes (selects last/largest)"""
        message = Mock()
        message.caption = "Photo with multiple sizes"
        message.media_group_id = "group_123"

        # Create multiple photo sizes (PhotoSize doesn't have mime_type)
        small_photo = Mock(spec=['get_file'])
        large_photo = Mock(spec=['get_file'])
        message.effective_attachment = [small_photo, large_photo]

        # Mock file for largest photo
        file_obj = AsyncMock()
        file_obj.file_path = "photos/large_photo.jpg"
        large_photo.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["mime_type"] == "image/jpeg"
        assert result["file_name"] == "large_photo.jpg"
        assert result["media_group_id"] == "group_123"

    @pytest.mark.asyncio
    async def test_handle_video_with_mime_type(self):
        """Test handling video message with explicit mime_type"""
        message = Mock()
        message.caption = "Test video"
        message.media_group_id = "video_group_456"

        video = Mock()
        video.mime_type = "video/mp4"
        video.file_id = "video_789"
        message.effective_attachment = video

        file_obj = AsyncMock()
        file_obj.file_path = "videos/video_789.mp4"
        video.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["mime_type"] == "video/mp4"
        assert result["file_name"] == "video_789.mp4"
        assert result["caption"] == "Test video"
        assert result["media_group_id"] == "video_group_456"

    @pytest.mark.asyncio
    async def test_handle_audio_file(self):
        """Test handling audio message"""
        message = Mock()
        message.caption = "Audio file"
        message.media_group_id = None

        audio = Mock()
        audio.mime_type = "audio/mp3"
        audio.file_id = "audio_456"
        message.effective_attachment = audio

        file_obj = AsyncMock()
        file_obj.file_path = "audio/song.mp3"
        audio.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["mime_type"] == "audio/mp3"
        assert result["file_name"] == "song.mp3"

    @pytest.mark.asyncio
    async def test_handle_pdf_document(self):
        """Test handling PDF document"""
        message = Mock()
        message.caption = "PDF document"
        message.media_group_id = None

        document = Mock()
        document.mime_type = "application/pdf"
        document.file_id = "doc_789"
        message.effective_attachment = document

        file_obj = AsyncMock()
        file_obj.file_path = "documents/report.pdf"
        document.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["mime_type"] == "application/pdf"
        assert result["file_name"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_unsupported_mime_type_returns_none(self):
        """Test that unsupported mime types return None"""
        message = Mock()
        message.caption = "Unsupported file"
        message.media_group_id = None

        document = Mock()
        document.mime_type = "application/zip"  # Not in SUPPORTED_MIME_TYPES
        message.effective_attachment = document

        result = await handle_input_media(message)

        assert result is None

    @pytest.mark.asyncio
    async def test_message_without_caption(self):
        """Test handling message without caption"""
        message = Mock()
        message.caption = None
        message.media_group_id = None

        # PhotoSize doesn't have mime_type
        photo = Mock(spec=['get_file'])
        message.effective_attachment = [photo]

        file_obj = AsyncMock()
        file_obj.file_path = "photos/no_caption.jpg"
        photo.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["caption"] is None
        assert result["mime_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_various_video_formats(self):
        """Test handling various supported video formats"""
        video_formats = [
            ("video/mp4", "video.mp4"),
            ("video/mpeg", "video.mpeg"),
            ("video/webm", "video.webm"),
            ("video/3gpp", "video.3gp")
        ]

        for mime_type, file_name in video_formats:
            message = Mock()
            message.caption = f"Test {mime_type}"
            message.media_group_id = None

            video = Mock()
            video.mime_type = mime_type
            message.effective_attachment = video

            file_obj = AsyncMock()
            file_obj.file_path = f"videos/{file_name}"
            video.get_file = AsyncMock(return_value=file_obj)

            result = await handle_input_media(message)

            assert result is not None
            assert result["mime_type"] == mime_type
            assert result["file_name"] == file_name

    @pytest.mark.asyncio
    async def test_various_image_formats(self):
        """Test handling various supported image formats"""
        image_formats = [
            ("image/png", "image.png"),
            ("image/webp", "image.webp"),
            ("image/heic", "image.heic"),
            ("image/heif", "image.heif")
        ]

        for mime_type, file_name in image_formats:
            message = Mock()
            message.caption = None
            message.media_group_id = None

            image = Mock()
            image.mime_type = mime_type
            message.effective_attachment = image

            file_obj = AsyncMock()
            file_obj.file_path = f"images/{file_name}"
            image.get_file = AsyncMock(return_value=file_obj)

            result = await handle_input_media(message)

            assert result is not None
            assert result["mime_type"] == mime_type

    @pytest.mark.asyncio
    async def test_various_audio_formats(self):
        """Test handling various supported audio formats"""
        audio_formats = [
            ("audio/wav", "audio.wav"),
            ("audio/mp3", "audio.mp3"),
            ("audio/ogg", "audio.ogg"),
            ("audio/flac", "audio.flac")
        ]

        for mime_type, file_name in audio_formats:
            message = Mock()
            message.caption = None
            message.media_group_id = None

            audio = Mock()
            audio.mime_type = mime_type
            message.effective_attachment = audio

            file_obj = AsyncMock()
            file_obj.file_path = f"audio/{file_name}"
            audio.get_file = AsyncMock(return_value=file_obj)

            result = await handle_input_media(message)

            assert result is not None
            assert result["mime_type"] == mime_type

    @pytest.mark.asyncio
    async def test_file_path_with_nested_directories(self):
        """Test correct extraction of filename from nested directory path"""
        message = Mock()
        message.caption = "Nested path"
        message.media_group_id = None

        document = Mock()
        document.mime_type = "application/pdf"
        message.effective_attachment = document

        file_obj = AsyncMock()
        file_obj.file_path = "documents/2024/reports/Q1/report.pdf"
        document.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["file_name"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_empty_caption_vs_none_caption(self):
        """Test handling of empty string caption vs None"""
        # Test with empty string
        message1 = Mock()
        message1.caption = ""
        message1.media_group_id = None

        # PhotoSize doesn't have mime_type
        photo = Mock(spec=['get_file'])
        message1.effective_attachment = [photo]

        file_obj = AsyncMock()
        file_obj.file_path = "photos/test.jpg"
        photo.get_file = AsyncMock(return_value=file_obj)

        result1 = await handle_input_media(message1)
        assert result1 is not None
        assert result1["caption"] == ""

    @pytest.mark.asyncio
    async def test_media_group_with_caption(self):
        """Test media group message with caption (usually last in group)"""
        message = Mock()
        message.caption = "Group caption"
        message.media_group_id = "group_999"

        # PhotoSize doesn't have mime_type
        photo = Mock(spec=['get_file'])
        message.effective_attachment = [photo]

        file_obj = AsyncMock()
        file_obj.file_path = "photos/group_photo.jpg"
        photo.get_file = AsyncMock(return_value=file_obj)

        result = await handle_input_media(message)

        assert result is not None
        assert result["caption"] == "Group caption"
        assert result["media_group_id"] == "group_999"


class TestSupportedMimeTypes:
    """Test suite for SUPPORTED_MIME_TYPES constant"""

    def test_supported_mime_types_contains_images(self):
        """Test that all expected image formats are supported"""
        expected_images = {
            "image/jpeg", "image/png", "image/webp",
            "image/heic", "image/heif"
        }
        assert expected_images.issubset(SUPPORTED_MIME_TYPES)

    def test_supported_mime_types_contains_videos(self):
        """Test that all expected video formats are supported"""
        expected_videos = {
            "video/mp4", "video/mpeg", "video/mov", "video/avi",
            "video/x-flv", "video/mpg", "video/webm", "video/wmv",
            "video/3gpp"
        }
        assert expected_videos.issubset(SUPPORTED_MIME_TYPES)

    def test_supported_mime_types_contains_audio(self):
        """Test that all expected audio formats are supported"""
        expected_audio = {
            "audio/wav", "audio/mp3", "audio/aiff", "audio/aac",
            "audio/ogg", "audio/flac"
        }
        assert expected_audio.issubset(SUPPORTED_MIME_TYPES)

    def test_supported_mime_types_contains_pdf(self):
        """Test that PDF is supported"""
        assert "application/pdf" in SUPPORTED_MIME_TYPES

    def test_unsupported_types_not_in_set(self):
        """Test that unsupported types are not in the set"""
        unsupported = [
            "application/zip", "application/x-rar-compressed",
            "text/plain", "application/msword"
        ]
        for mime_type in unsupported:
            assert mime_type not in SUPPORTED_MIME_TYPES