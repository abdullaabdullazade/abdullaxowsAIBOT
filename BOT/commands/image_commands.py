import discord
from discord.ext import commands
from discord import app_commands
from AI.text_ai import TextAIHandler
from BOT.handler import DiscordResponseHandler
import os


class ImagineCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()

    @app_commands.command(
        name="imagine",
        description="Describe a scene and the AI will generate an image for you 🎨",
    )
    @app_commands.describe(prompt="Describe the scene or concept you imagine.")
    async def imagine(self, interaction: discord.Interaction, prompt: str) -> None:
        """
        Generates an AI image based on the user's prompt.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
            prompt (str): The user's description of the imagined scene.
        """
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        image_path, reply_text = await self.handler.generate_imagine_response(
            prompt, user_id
        )

        if image_path:
            file = discord.File(image_path)
            await interaction.followup.send(content=reply_text, file=file)
            os.remove(image_path)
        else:
            await interaction.followup.send(content=reply_text)

    @app_commands.command(
        name="promptlab",
        description="Enhance your prompt and generate an AI image! 🖋️",
    )
    @app_commands.describe(
        prompt="🖋️ Describe your imagined scene or concept, and I’ll turn it into a vivid and creative prompt for image generation!"
    )
    async def promptlab(self, interaction: discord.Interaction, prompt: str) -> None:
        """
        Enhances a user's prompt and generates an AI image based on it.

        Args:
            interaction (discord.Interaction): The interaction object from Discord.
            prompt (str): The user's initial idea or description.

        This function:
        - Enhances the user's text prompt.
        - Responds with either the image and explanation, or a fallback message.
        """

        await interaction.response.defer(thinking=True)
        nickname = interaction.user.display_name

        response = await self.textai_handler.get_promptlab(prompt)
        response = f"```{response}\n```"
        await self.handler.safe_embed_reply(
            interaction, response, nickname, title="✨ Prompt"
        )
