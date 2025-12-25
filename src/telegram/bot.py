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

from src.mongo import get_or_create_user, append_user_message, append_bot_response

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # Store user in MongoDB
    await get_or_create_user(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username
    )
    
    # Store the /start command as user message
    await append_user_message(
        user_id=user.id,
        chat_id=chat_id,
        message_id=message.message_id,
        message_text="/start"
    )
    
    # Send and store response
    response_text = "Kya Hua Pathe? (Whats up bro?)"
    sent_message = await message.reply_text(response_text)
    
    await append_bot_response(
        user_id=user.id,
        chat_id=chat_id,
        message_id=sent_message.message_id,
        response_text=response_text
    )

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # Ensure user exists in MongoDB
    await get_or_create_user(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username
    )
    
    # Store user's message
    await append_user_message(
        user_id=user.id,
        chat_id=chat_id,
        message_id=message.message_id,
        message_text=message.text
    )
    
    # Send and store response
    response_text = "Abhi thoda kaam chalra pathe, thodi der baad message karro!"
    sent_message = await message.reply_text(response_text)
    
    await append_bot_response(
        user_id=user.id,
        chat_id=chat_id,
        message_id=sent_message.message_id,
        response_text=response_text
    )

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