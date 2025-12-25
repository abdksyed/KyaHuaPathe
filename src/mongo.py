import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# MongoDB connection
_client: Optional[AsyncIOMotorClient] = None
_db = None


def get_client() -> AsyncIOMotorClient:
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        mongodb_url = os.environ.get("MONGODB_URL")
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is not set")
        _client = AsyncIOMotorClient(mongodb_url)
    return _client


def get_db():
    """Get the database instance."""
    global _db
    if _db is None:
        client = get_client()
        _db = client.kyahuapathe
    return _db


async def get_or_create_user(user_id: int, first_name: str = None, last_name: str = None, username: str = None) -> dict:
    """
    Get existing user or create a new one.
    
    Args:
        user_id: Telegram user ID (e.g., 75126997)
        first_name: User's first name
        last_name: User's last name
        username: User's telegram username
    
    Returns:
        User document from MongoDB
    """
    db = get_db()
    users = db.users
    
    user = await users.find_one({"user_id": user_id})
    
    if user is None:
        user = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await users.insert_one(user)
    else:
        # Update user info if changed
        update_fields = {}
        if first_name and user.get("first_name") != first_name:
            update_fields["first_name"] = first_name
        if last_name and user.get("last_name") != last_name:
            update_fields["last_name"] = last_name
        if username and user.get("username") != username:
            update_fields["username"] = username
        
        if update_fields:
            update_fields["updated_at"] = datetime.now(timezone.utc)
            await users.update_one(
                {"user_id": user_id},
                {"$set": update_fields}
            )
            user = await users.find_one({"user_id": user_id})
    
    return user


async def append_user_message(user_id: int, chat_id: int, message_id: int, message_text: str) -> dict:
    """
    Store a user's incoming message.
    
    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        message_id: Telegram message ID
        message_text: The message content
    
    Returns:
        The inserted message document
    """
    db = get_db()
    messages = db.messages
    
    message_doc = {
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "role": "user",
        "content": message_text,
        "timestamp": datetime.now(timezone.utc),
    }
    
    await messages.insert_one(message_doc)
    return message_doc


async def append_bot_response(user_id: int, chat_id: int, message_id: int, response_text: str) -> dict:
    """
    Store a bot's response message.
    
    Args:
        user_id: Telegram user ID (who the response is for)
        chat_id: Telegram chat ID
        message_id: Telegram message ID of the response
        response_text: The bot's response content
    
    Returns:
        The inserted message document
    """
    db = get_db()
    messages = db.messages
    
    message_doc = {
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now(timezone.utc),
    }
    
    await messages.insert_one(message_doc)
    return message_doc


async def get_user_chat_history(user_id: int, chat_id: int = None, limit: int = 50) -> list:
    """
    Get chat history for a user.
    
    Args:
        user_id: Telegram user ID
        chat_id: Optional chat ID to filter by specific chat
        limit: Maximum number of messages to return (default 50)
    
    Returns:
        List of message documents sorted by timestamp (oldest first)
    """
    db = get_db()
    messages = db.messages
    
    query = {"user_id": user_id}
    if chat_id:
        query["chat_id"] = chat_id

    # Sort by timestamp (1 = ascending, -1 = descending)
    # Use -1 for most recent messages first, 1 for chronological order
    cursor = messages.find(query).sort("timestamp", 1).limit(limit)
    return await cursor.to_list(length=limit)


async def close_connection():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None