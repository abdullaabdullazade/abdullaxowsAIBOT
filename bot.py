"""
Discord Bot (abdullaxows-ai)

This bot is designed to interact with users via text, image, and voice messages on Discord. It uses AI-powered backends to:
- Respond to text messages in a natural, intelligent way.
- Analyze and interpret image attachments.
- Generate AI images based on text or voice prompts.
- Transcribe audio and respond accordingly.

The bot supports both text and voice replies and uses a modular class-based structure for scalability and maintainability.
"""

import discord
from discord import Message
import asyncio
import os
from discord.ext import commands
from database.db import DatabaseManager
from AI.text_ai import TextAIHandler
from BOT.handler import DiscordResponseHandler
from BOT.bot_config import DISCORD_BOT_TOKEN
from logger_config import logger
from BOT.reminder import ReminderHandler
from BOT.commands.image_commands import ImagineCommands
from BOT.commands.mode_commands import ModeCommands
from BOT.commands.mode_switch_commands import ModeSwitchCommands
from BOT.commands.memory_commands import MemoryCommands
from BOT.commands.utility_commands import UtilityCommands
from BOT.commands.reminder_commands import ReminderCommands
from BOT.commands.interesting_commands import InterestingCommands


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


class BotController:
    """
    Main controller class for handling Discord bot events and message processing.
    Responsible for:
    - Responding to text, image, and voice messages.
    - Integrating AI models for text generation, image analysis, and speech-to-text.
    - Managing user information and conversation history.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()
        self.reminder_handler = ReminderHandler()

    async def setup(self):
        """Create necessary directories and load bot commands."""
        os.makedirs("media", exist_ok=True)
        os.makedirs("media/images", exist_ok=True)
        os.makedirs("media/out", exist_ok=True)
        os.makedirs("media/audio", exist_ok=True)
        os.makedirs("media/files", exist_ok=True)
        for i in [
            ImagineCommands,
            ModeCommands,
            ModeSwitchCommands,
            MemoryCommands,
            UtilityCommands,
            ReminderCommands,
            InterestingCommands,
        ]:
            await self.bot.add_cog(i(self.bot))

    async def on_ready(self):
        """Initialize database and synchronize bot commands when ready."""
        await self.db.setup_db()
        await self.bot.wait_until_ready()
        await self.bot.tree.sync()
        self.bot.loop.create_task(self.reminder_handler.reminder_loop(self.bot))

        await self.bot.change_presence(
            activity=discord.Game(name="Chatting with you 👀")
        )
        logger.info(f"{self.bot.user} connected.")

    async def on_message(self, message: Message) -> None:
        """Main message handler for processing text, and voice content."""
        await self.bot.process_commands(message)
        if message.author == self.bot.user:
            return

        user_id = str(message.author.id)
        if await self.db.get_message_type(user_id) is None:
            await self.db.set_message_type(user_id, "text")
        if await self.db.get_mode(user_id) is None:
            await self.db.set_mode(user_id, 1)
        user_message_type = await self.db.get_message_type(user_id)

        nickname = str(message.author.display_name)
        content = message.content.strip()
        channel_id = str(message.channel.id)
        await self.db.update_user_info(user_id, nickname)
        chat_mode = await self.db.get_mode(user_id)
        logger.info(chat_mode)
        if not chat_mode:
            return

        if await self.db.get_response_count(user_id) % 10 == 0:
            response = await self.textai_handler.delete_useless_messages(user_id)
            await self.db.delete_by_id(response)

        if message.attachments:
            await message.channel.typing()
            file = message.attachments[0]
            if self.handler.check_image(file):
                await self.handler.process_image_attachment(
                    message, file, content, user_id, user_message_type, channel_id
                )
                return
            if file.content_type and "audio" in file.content_type:
                await self.handler.process_audio_attachment(
                    message, file, user_id, user_message_type, channel_id
                )
                return
            else:
                save_path = f"media/files/{file.filename}"
                await file.save(save_path)

                await self.handler.analyze_document(
                    message, user_message_type, save_path, user_id, channel_id, content
                )
                return

        await self.handler.process_text_message(
            message, user_id, user_message_type, channel_id, content
        )


controller = BotController(bot)


@bot.event
async def on_ready():
    await controller.on_ready()


@bot.event
async def on_message(message):
    await controller.on_message(message)


if __name__ == "__main__":
    asyncio.run(controller.setup())
    bot.run(DISCORD_BOT_TOKEN)
