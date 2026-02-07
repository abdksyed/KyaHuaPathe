import asyncio
import os
from collections import defaultdict
from functools import partial
from typing import Iterable

import telegramify_markdown
from telegram.constants import MessageLimit
from telegram.ext import (
    Application,  # main class
    CommandHandler,  # to handle / commands like /start
    ContextTypes,  # type for callback context
    MessageHandler,  # text messages
    filters,  # filtering message types
)

from src.agent import agent_service
from src.telegram.filter import InputMediaInfo, handle_input_media
from telegram import ReplyParameters, Update  # for incoming updates from telegram

# Store application globally for lifespan management
application = None
MAX = MessageLimit.MAX_TEXT_LENGTH  # 4096

MEDIA_GROUP_BUFFER = defaultdict(list)
# To track the scheduled jobs for media groups
SCHEDULED_JOBS = {}
MAX_WAIT_TIME_FOR_NEXT_MEDIA = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kya Hua Pathe? (Whats up bro?)")


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agent_service.run_query(
        message=update.message.text,
        user_id=str(update.message.from_user.id),
        session_id=str(update.message.from_user.id),
        callback=partial(
            send_reply_to_chat,
            bot=context.bot,
            chat_id=update.message.chat_id,
            reply_message_id=update.message.message_id,
        ),
    )


async def reply_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media_info: InputMediaInfo | None = await handle_input_media(update.message)
    time_to_wait_before_process = MAX_WAIT_TIME_FOR_NEXT_MEDIA
    if not media_info:
        await update.message.reply_text("I don't support this media type yet.")
        return

    # if media_group_id is None, it means it is a single media
    # we assign the message id as group id and send it to processing
    media_group_id = media_info.media_group_id
    if not media_group_id:
        time_to_wait_before_process = 0
        media_group_id = str(update.message.message_id)
    MEDIA_GROUP_BUFFER[media_group_id].append(media_info)

    # If the media group id has already been scheduled, cancel the job
    # Case: for 2nd, 3rd, ... media in a group
    if media_group_id in SCHEDULED_JOBS:
        SCHEDULED_JOBS[media_group_id].schedule_removal()

    # Schedule the media group processing after a delay
    # Only store primitives in job.data to avoid pinning large objects
    job = context.job_queue.run_once(
        process_media,
        when=time_to_wait_before_process,
        data={
            "media_group_id": media_group_id,
            "user_id": str(update.message.from_user.id),
            "session_id": str(update.message.from_user.id),
            "chat_id": update.message.chat_id,
            "reply_message_id": update.message.message_id,
        },
    )
    SCHEDULED_JOBS[media_group_id] = job
    await update.message.reply_text(f"Received {media_info.file_name}")


async def process_media(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    media_group_id = job.data["media_group_id"]
    user_id = job.data["user_id"]
    session_id = job.data["session_id"]
    chat_id = job.data["chat_id"]
    reply_message_id = job.data["reply_message_id"]

    # pop the media group
    media_group = MEDIA_GROUP_BUFFER.pop(media_group_id, [])
    # remove the job from scheduled jobs
    SCHEDULED_JOBS.pop(media_group_id, None)

    # Download all the media
    downloaded_media = await asyncio.gather(
        *[media.file_obj.download_as_bytearray() for media in media_group],
        return_exceptions=True,
    )
    # remove any exceptions
    downloaded_media = [
        (media_bytes, media.mime_type)
        for media_bytes, media in zip(downloaded_media, media_group, strict=True)
        if not isinstance(media_bytes, Exception)
    ]
    if not downloaded_media:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Couldn't download media, can you please try again?",
            reply_parameters=ReplyParameters(
                message_id=reply_message_id, chat_id=chat_id
            ),
        )
        return
    caption = next((media.caption for media in media_group if media.caption), "")

    # Run the agent
    await agent_service.run_query_with_media(
        message=caption,
        media_list=downloaded_media,
        user_id=user_id,
        session_id=session_id,
        callback=partial(
            send_reply_to_chat,
            bot=context.bot,
            chat_id=chat_id,
            reply_message_id=reply_message_id,
        ),
    )


async def send_reply_to_chat(message: str, bot, chat_id: int, reply_message_id: int):
    """Send reply using bot.send_message instead of update object (for use in scheduled jobs)."""
    formatted_message = telegramify_markdown.markdownify(message)
    if not formatted_message or not formatted_message.strip():
        formatted_message = "No response"

    def chunk(text: str, n: int = MAX) -> Iterable[str]:
        for i in range(0, len(text), n):
            yield text[i : i + n]

    for chunk_text in chunk(formatted_message):
        await bot.send_message(
            chat_id=chat_id,
            text=chunk_text,
            parse_mode="MarkdownV2",
            reply_parameters=ReplyParameters(
                message_id=reply_message_id,
                allow_sending_without_reply=True,
            ),
        )


async def start_bot():
    """Start the Telegram bot (non-blocking for FastAPI integration)"""
    global application
    application = (
        Application.builder()
        .token(os.environ.get("TELEGRAM_BOT_TOKEN"))
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    media_filter = (
        filters.PHOTO
        | filters.VIDEO
        | filters.AUDIO
        | filters.VOICE
        | filters.VIDEO_NOTE
        | filters.Document.ALL
    )
    application.add_handler(
        MessageHandler(media_filter & ~filters.COMMAND, reply_for_media)
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling()


async def stop_bot():
    """Stop the Telegram bot gracefully"""
    global application
    if application:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
