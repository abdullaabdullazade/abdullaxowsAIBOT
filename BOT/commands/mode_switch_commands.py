import discord
from discord.ext import commands
from discord import app_commands
from database.db import DatabaseManager


class ModeSwitchCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()

    @app_commands.command(name="off", description="Mute the bot in this chat 😶")
    async def off(self, interaction: discord.Interaction):
        """
        Disables the bot's responses in the current channel.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """
        await self.db.set_mode(interaction.user.id, 0)
        await interaction.response.send_message(
            "I will remain silent in this channel 😶"
        )

    @app_commands.command(name="on", description="Unmute the bot in this chat 😄")
    async def on(self, interaction: discord.Interaction):
        """
        Re-enables the bot's responses in the current channel.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
        """

        await self.db.set_mode(interaction.user.id, 1)
        await interaction.response.send_message("I'm active again in this channel 😄")
