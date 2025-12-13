import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

from src.telegram import bot

def main():
    if len(sys.argv) > 2 or len(sys.argv) == 1:
        raise ValueError("Invalid number of arguments. Usage: python main.py <bot_type>")
    
    bot_type = sys.argv[1]
    if bot_type not in ["telegram", "discord", "whatsapp"]:
        raise ValueError("Invalid bot type")
    
    if bot_type == "telegram":
        asyncio.run(bot.init())
    elif bot_type == "discord":
        raise NotImplementedError("Discord bot not implemented yet")
    elif bot_type == "whatsapp":
        raise NotImplementedError("Whatsapp bot not implemented yet")
    

if __name__ == "__main__":
    main()
