import discord
from discord.ext import commands
from discord import app_commands
from AI.text_ai import TextAIHandler
from BOT.handler import DiscordResponseHandler
import os

from database.db import DatabaseManager


class MemoryCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()
        self.db = DatabaseManager()

    @app_commands.command(
        name="memory", description="Summarize your memory with the AI 🧠"
    )
    async def memory(self, interaction: discord.Interaction):
        """
        Summarizes the user's stored memory and sends it as embeds.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        nickname = interaction.user.display_name
        await self.db.update_user_info(user_id, nickname)

        summary = await self.textai_handler.summarize_user_memory(user_id, nickname)
        await self.handler.safe_embed_reply(
            interaction, summary, nickname, title="🧠 Memory Summary"
        )

    @app_commands.command(name="reset", description="Reset all chat history 🧹")
    async def reset(self, interaction: discord.Interaction):
        """
        Clears the user's stored conversation history.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        user_id = str(interaction.user.id)
        await self.db.reset_chat(user_id)
        await interaction.response.send_message("Chat history has been reset! 🧹")
