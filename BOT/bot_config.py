"""
This module configures the Discord bot.
It loads BOT tokens and bot name.
"""

from dotenv import load_dotenv
import os

load_dotenv()


# GET BOT TOKEN FROM .ENV
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


BOT_NAME = os.getenv("BOT_NAME") 
