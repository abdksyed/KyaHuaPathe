from collections.abc import Iterable
from dataclasses import dataclass
from telegram import Message, File

SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "video/mp4",
    "video/mpeg",
    "video/mov",
    "video/avi",
    "video/x-flv",
    "video/mpg",
    "video/webm",
    "video/wmv",
    "video/3gpp",
    "application/pdf",
    "audio/wav",
    "audio/mp3",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
}


@dataclass
class InputMediaInfo:
    """Typed container for parsed Telegram media input."""

    mime_type: str
    file_name: str
    caption: str | None
    media_group_id: str | None
    file_obj: File


# Major Caveat: In telegram, when someone sends a group of media files, it is NOT sent as a single message
# rather it is send as an individual message for each file.
# But all the media sent together will have a common `media_group_id`
# The caption if present will be present for the last message in the group
async def handle_input_media(message: Message) -> InputMediaInfo | None:
    caption = message.caption
    media_group_id = message.media_group_id
    attachment = message.effective_attachment
    if isinstance(attachment, Iterable):
        # generally, only the Photo is send as a list
        attachment = attachment[-1]

    # PhotoSize doesn't have mime_type, becuase images in telegram are always jpeg
    mime_type = (
        attachment.mime_type if hasattr(attachment, "mime_type") else "image/jpeg"
    )
    if mime_type not in SUPPORTED_MIME_TYPES:
        return None
    file_obj = await attachment.get_file()
    file_name = (
        attachment.file_name
        if hasattr(attachment, "file_name")
        else file_obj.file_path.split("/")[-1]
    )

    return InputMediaInfo(
        mime_type=mime_type,
        file_name=file_name,
        caption=caption,
        media_group_id=media_group_id,
        file_obj=file_obj,
    )
