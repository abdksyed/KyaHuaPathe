import asyncio
import os
from collections import defaultdict
from functools import partial

from telegram import Update, User  # for incoming updates from telegram
from telegram.ext import (
    Application, # main class 
    CommandHandler, # to handle / commands like /start
    MessageHandler, # text messages
    filters, # filtering message types
    ContextTypes, # type for callback context
)
import telegramify_markdown
from telegram.constants import MessageLimit

from src.agent import agent_service
from src.telegram.filter import handle_input_media

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
        callback=partial(format_and_send_reply, update=update)
    )

async def reply_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media_info = await handle_input_media(update.message)
    time_to_wait_before_process = MAX_WAIT_TIME_FOR_NEXT_MEDIA
    if not media_info:
        await update.message.reply_text("I don't support this media type yet.")
        return
    
    # if media_group_id is None, it means it is a single media
    # we assign the message id as group id and send it to processing
    media_group_id = media_info["media_group_id"]
    if not media_group_id:
        time_to_wait_before_process = 0
        media_group_id = str(update.message.message_id)
    MEDIA_GROUP_BUFFER[media_group_id].append(media_info)
    
    # If the media group id has already been scheduled, cancel the job
    # Case: for 2nd, 3rd, ... media in a group
    if media_group_id in SCHEDULED_JOBS:
        SCHEDULED_JOBS[media_group_id].schedule_removal()
        
    # Schedule the media group processing after a delay
    job = context.job_queue.run_once(
        process_media,
        when = time_to_wait_before_process,
        data = {
            "media_group_id": media_group_id,
            "user_id": update.message.from_user.id,
            "session_id": update.message.from_user.id,
            "update": update,
            "context": context
        }
    )
    SCHEDULED_JOBS[media_group_id] = job
    await update.message.reply_text(f"Received {media_info['file_name']}")

async def process_media(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    media_group_id = job.data["media_group_id"]
    user_id = job.data["user_id"]
    session_id = job.data["session_id"]
    update = job.data["update"]
    context = job.data["context"]
    media_group = MEDIA_GROUP_BUFFER[media_group_id]
    # Download all the media
    downloaded_media = await asyncio.gather(
        *[media["file_obj"].download_as_bytearray() for media in media_group],
        return_exceptions=True
    )
    # remove any exceptions
    downloaded_media = [
        (media_bytes, media["mime_type"]) for media_bytes, media in zip(downloaded_media, media_group) if not isinstance(media, Exception)
    ]
    if not downloaded_media:
        await update.message.reply_text("Couldn't download media, can you please try again?")
        return
    caption = next((media["caption"] for media in media_group if media["caption"]), "")

    # Run the agent
    await agent_service.run_query_with_media(
        message=caption,
        media_list=downloaded_media,
        user_id=str(user_id),
        session_id=str(session_id),
        callback=partial(format_and_send_reply, update=update)
    )   

async def format_and_send_reply(message: str, update: Update):
    # Convert LLM markdown to Telegram MarkdownV2 format
    formatted_message = telegramify_markdown.markdownify(message)
    def chunk(text, n=MAX):
        for i in range(0, len(text), n):
            yield text[i:i+n]
    for chunk_text in chunk(formatted_message):
        await update.message.reply_text(chunk_text, parse_mode="MarkdownV2")


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
        filters.PHOTO | 
        filters.VIDEO | 
        filters.AUDIO | 
        filters.VOICE | 
        filters.VIDEO_NOTE |
        filters.Document.ALL
    )
    application.add_handler(MessageHandler(media_filter & ~filters.COMMAND, reply_for_media))
    
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