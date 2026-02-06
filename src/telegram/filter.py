from dataclasses import dataclass
from enum import Enum
from telegram import Update, Message, File

class MediaType(Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    VIDEO_NOTE = "video_note"

SUPPORTED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
    "video/mp4", "video/mpeg", "video/mov", "video/avi", "video/x-flv", "video/mpg", "video/webm", "video/wmv", "video/3gpp",
    "application/pdf",
    "audio/wav", "audio/mp3", "audio/aiff", "audio/aac", "audio/ogg", "audio/flac"
}

@dataclass
class MediaInfo:
    media_type: MediaType
    file_obj: File
    caption: str
    media_group_id: str
    file_name: str
    mime_type: str

    # download the file
    async def download(self):
        return await self.file_obj.download_as_bytearray()

# Major Caveat: In telegram, when someone sends a group of media files, it is NOT sent as a single message
# rather it is send as an individual message for each file.
# But all the media sent together will have a common `media_group_id`
# The caption if present will be present for the last message in the group
async def handle_input_media(message: Message):
    caption = message.caption
    media_group_id = message.media_group_id
    attachment = message.effective_attachment
    if isinstance(attachment, list):
        # generally, only the Photo is send as a list
        file_obj = await attachment[-1].get_file()
    else:
        file_obj = await attachment.get_file()
    
    if attachment.mime_type not in SUPPORTED_MIME_TYPES:
        return None
    
    file_name = attachment.file_name
    mime_type = attachment.mime_type

    return {
        "mime_type": mime_type,
        "file_name": file_name,
        "caption": caption,
        "media_group_id": media_group_id,
        "file_obj": file_obj,
    }

    

    # # Determine the media type and get the file
    # if message.photo:
    #     # Imp: photos come as a list, and the last one is the highest resolution
    #     file_obj: File = await message.photo[-1].get_file()
    #     file_name = message.photo[-1].file_name
    #     media_type = MediaType.PHOTO
    #     mime_type = message.photo[-1].mime_type
    # elif message.video:
    #     file_obj: File = await message.video.get_file()
    #     file_name = message.video.file_name
    #     media_type = MediaType.VIDEO
    #     mime_type = message.video.mime_type
    # elif message.audio:
    #     file_obj: File = await message.audio.get_file()
    #     file_name = message.audio.file_name
    #     media_type = MediaType.AUDIO
    #     mime_type = message.audio.mime_type
    # elif message.voice:
    #     file_obj: File = await message.voice.get_file()
    #     file_name = message.voice.file_name
    #     media_type = MediaType.VOICE
    #     mime_type = message.voice.mime_type
    # elif message.document:
    #     file_obj: File = await message.document.get_file()
    #     file_name = message.document.file_name
    #     media_type = MediaType.DOCUMENT
    #     mime_type = message.document.mime_type
    # elif message.video_note:
    #     file_obj: File = await message.video_note.get_file()
    #     file_name = message.video_note.file_name
    #     media_type = MediaType.VIDEO_NOTE
    #     mime_type = message.video_note.mime_type
    # else:
    #     return None

    # return MediaInfo(
    #     media_type=media_type,
    #     file_obj=file_obj,
    #     caption=caption,
    #     media_group_id=media_group_id,
    #     file_name=file_name,
    #     mime_type=mime_type
    # )


    
        
    