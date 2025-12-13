import asyncio
import os

from telegram import Update  # for incoming updates from telegram
from telegram.ext import (
    Application, # main class 
    CommandHandler, # to handle / commands like /start
    MessageHandler, # text messages
    filters, # filtering message types
    ContextTypes # type for callback context
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kya Hua Pathe? (Whats up bro?)")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Abhi thoda kaam chalra pathe, thodi der baad message karro!")

def init():
    # Build your application  
    application = Application.builder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    asyncio.run(init())