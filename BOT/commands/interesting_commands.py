from discord import app_commands, Interaction
from discord.ext import commands
from AI.text_ai import TextAIHandler
from database.db import DatabaseManager
from BOT.handler import DiscordResponseHandler
from logger_config import logger
from prompt import format_prompt
from utils import async_wrap_blocking
from AI.ai_config import GEMINI_AI
import asyncio


class InterestingCommands(commands.Cog):
    """
    A Discord Cog that provides interesting AI-generated content,
    including facts, quotes, and code explanations.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()
        self.db = DatabaseManager()

    @app_commands.command(
        name="getfacts", description="📚 Get today's interesting AI fact."
    )
    async def get_facts(self, interaction: Interaction):
        """Sends a random AI-generated interesting fact."""
        try:
            await interaction.response.defer(thinking=True)

            fact = await self.textai_handler.get_facts(interaction.user.id)
            username = interaction.user.display_name

            await self.handler.safe_embed_reply(
                interaction, fact, username, title="📚 AI Fact of the Day"
            )

        except Exception as e:
            logger.error(f"🚨 Error retrieving AI fact: {e}")
            await interaction.edit_original_response(
                content="⚠️ An error occurred while retrieving the fact."
            )

    @app_commands.command(
        name="quote",
        description="🧠 Get a motivational or philosophical quote from AI.",
    )
    async def quote(self, interaction: Interaction):
        """Sends a short inspirational or philosophical quote."""
        try:
            await interaction.response.defer(thinking=True)
            nickname = interaction.user.display_name

            prompt = format_prompt("quote")

            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, prompt), timeout=25
            )

            await self.handler.safe_embed_reply(
                interaction,
                response.text.strip(),
                nickname,
                title="🧠 Quote of the Moment",
            )

        except Exception as e:
            logger.error(f"🚨 Error generating quote: {e}")
            await interaction.edit_original_response(
                content="⚠️ An error occurred while generating the quote."
            )

    @app_commands.command(
        name="explain_code", description="💻 Let the AI explain a piece of code to you."
    )
    @app_commands.describe(code="Paste the code you want explained.")
    async def explain_code(self, interaction: Interaction, code: str):
        """Explains a code snippet in beginner-friendly language."""
        try:
            await interaction.response.defer(thinking=True)
            nickname = interaction.user.display_name

            prompt = format_prompt("explain_code", code=code)

            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, prompt), timeout=25
            )
            await self.db.save_history(interaction.user.id, code, response.text.strip())

            await self.handler.safe_embed_reply(
                interaction,
                response.text.strip(),
                nickname,
                title="💡 Code Explanation",
            )

        except Exception as e:
            logger.error(f"🚨 Error explaining code: {e}")
            await interaction.edit_original_response(
                content="⚠️ An error occurred while explaining the code."
            )
