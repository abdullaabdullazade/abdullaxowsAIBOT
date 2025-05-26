import discord
from discord.ext import commands
from discord import app_commands
from database.db import DatabaseManager


class ModeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()

    @app_commands.command(name="voice", description="Switch to voice response mode 🎤")
    async def voice(self, interaction: discord.Interaction):
        """
        Switches the response mode to voice replies.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        await self.db.set_message_type(interaction.user.id, "speech")
        await interaction.response.send_message("I will now respond with voice! 🎤")

    @app_commands.command(name="text", description="Switch to text response mode 💬")
    async def text(self, interaction: discord.Interaction):
        """
        Switches the response mode to text replies.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        await self.db.set_message_type(interaction.user.id, "text")
        await interaction.response.send_message("I will now respond with text! 💬")

    @app_commands.command(name="image", description="Switch to image generation mode 🖼️")
    async def image(self, interaction: discord.Interaction):
        """
        Switches the response mode to image generation.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        await self.db.set_message_type(interaction.user.id, "image")
        await interaction.response.send_message("I will now generate images! 🖼️")
