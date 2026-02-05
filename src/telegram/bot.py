import os
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

# Store application globally for lifespan management
application = None
MAX = MessageLimit.MAX_TEXT_LENGTH  # 4096

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kya Hua Pathe? (Whats up bro?)")


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agent_service.run_query(
        message=update.message.text,
        user_id=str(update.message.from_user.id),
        session_id=str(update.message.from_user.id),
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