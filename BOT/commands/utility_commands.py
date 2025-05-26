import discord
from discord.ext import commands
from discord import app_commands
from AI.text_ai import TextAIHandler
from BOT.handler import DiscordResponseHandler
from database.db import DatabaseManager
from AI.search_ai import SmartGoogleSearcher
from logger_config import logger
from AI.weather_ai import Weather
from discord import Interaction, Embed
from AI.summarize_url_with_ai import SummarizeURL


class UtilityCommands(commands.Cog):
    """Collection of utility slash commands for Discord bot."""

    def __init__(self, bot: commands.Bot):
        """Initializes command handlers and AI services."""
        self.bot = bot
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()
        self.db = DatabaseManager()
        self.search_handler = SmartGoogleSearcher()
        self.weather = Weather()
        self.summarize_url = SummarizeURL()

    @app_commands.command(
        name="summarize_url",
        description="🔗 Summarize a webpage content with browser simulation.",
    )
    @app_commands.describe(url="The URL of the page you want to summarize.")
    async def summarize_url_(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        nickname = interaction.user.display_name

        try:
            response = await self.summarize_url.summarize_url(url, user_id)
            await self.handler.safe_embed_reply(
                interaction, response, nickname, title="🔗 URL Summary"
            )
        except Exception as e:
            logger.error(f"🚨 Error summarizing URL: {e}")
            await interaction.followup.send(
                "❌ An error occurred while summarizing the URL."
            )

    @app_commands.command(
        name="search", description="🔍 Search the web and get a summary of the results!"
    )
    @app_commands.describe(query="🔍 Enter your search query here.")
    async def search(self, interaction: discord.Interaction, query: str):
        """
        Performs a web search and summarizes the results.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
            query (str): The user's search query.

        Returns:
            None
        """
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        nickname = interaction.user.display_name

        response = await self.search_handler.smart_search_response(user_id, query)
        await self.handler.safe_embed_reply(
            interaction, response, nickname, title="🔍 Search Results"
        )

    @app_commands.command(
        name="weather", description="☀️ Get the weather forecast for a specific city."
    )
    @app_commands.describe(
        city="🔎 Name of the city you want the weather forecast for."
    )
    async def weather_(self, interaction: discord.Interaction, city: str):
        """
        Retrieves and sends weather forecast for the given city.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
            city (str): City name to fetch weather for.

        Returns:
            None
        """
        await interaction.response.defer(thinking=True)
        data = await self.weather.fetch_weather(city)

        if data:
            weather_description = data["weather"][0]["description"].capitalize()
            temperature = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            embed = discord.Embed(
                title=f"🌍 {city} Weather Forecast",
                description=f"**{weather_description}**",
                color=discord.Color.blue(),
            )
            embed.add_field(name="🌡️ Temperature", value=f"{temperature}°C", inline=True)
            embed.add_field(name="🤔 Feels Like", value=f"{feels_like}°C", inline=True)
            embed.add_field(name="💧 Humidity", value=f"%{humidity}", inline=True)
            embed.add_field(
                name="💨 Wind Speed", value=f"{wind_speed} m/s", inline=True
            )
            embed.set_footer(text="🔎 Powered by OpenWeather")

            await self.db.save_history(
                interaction.user.id, city, f"Weather in {city}: {weather_description}"
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Sorry, no weather found for `{city}`.")


    @app_commands.command(
        name="help", description="📚 Get a list of available commands."
    )
    async def help(self, interaction: Interaction):
        embed = Embed(
            title="📘 Help – Available Commands",
            description="Here are the commands you can use with `abdullaxowsai`:",
            color=0x2ECC71,
        )

        embed.add_field(
            name="🎨 `/imagine`",
            value="Generate AI image from a description",
            inline=False,
        )
        embed.add_field(
            name="🧠 `/memory`",
            value="Summarize what the bot remembers about you",
            inline=False,
        )
        embed.add_field(
            name="🗣️ `/voice`, `/text`, `/image`",
            value="Switch between voice, text, or image mode",
            inline=False,
        )
        embed.add_field(
            name="🎯 `/promptlab`",
            value="Turn your idea into a vivid image prompt",
            inline=False,
        )
        embed.add_field(
            name="🔍 `/search`",
            value="Search Google and summarize results",
            inline=False,
        )
        embed.add_field(
            name="📅 `/remind_add`",
            value="Set a reminder with time & message",
            inline=False,
        )
        embed.add_field(
            name="📝 `/remind_list`, `/remind_delete`",
            value="List or delete reminders",
            inline=False,
        )
        embed.add_field(
            name="🌤️ `/weather`", value="Check real-time weather of a city", inline=False
        )
        embed.add_field(
            name="📚 `/getfacts`", value="Get a fun AI fact of the day", inline=False
        )
        embed.add_field(
            name="😶 `/off`, `/on`",
            value="Mute or activate bot in this channel",
            inline=False,
        )

        embed.set_footer(text="Need help with anything else? Just ask!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="about", description="🤖 Learn more about the abdullaxowsai bot."
    )
    async def about(self, interaction: Interaction):
        embed = Embed(
            title="🤖 abdullaxowsai – Smart, Safe, and Modular AI Bot",
            description="Created with ❤️ by **Abdulla**, this bot combines conversational AI, image processing, "
            "voice, document analysis, and safety-aware generation. It's not just a bot — it's a smart assistant.",
            color=0x3498DB,
        )

        embed.add_field(
            name="🧠 Multi-modal Intelligence",
            value="Text, Voice, Image generation and analysis",
            inline=False,
        )
        embed.add_field(
            name="🎨 Creative Tools",
            value="Imagine prompts, PromptLab enhancer, Drawing tools",
            inline=False,
        )
        embed.add_field(
            name="📁 Document Analysis",
            value="Supports `.pdf`, `.docx`, `.xlsx`, `.csv` file scanning",
            inline=False,
        )
        embed.add_field(
            name="🌍 Smart Web Search",
            value="Google search + AI summarization",
            inline=False,
        )
        embed.add_field(
            name="⏰ Reminders & Weather",
            value="Create reminders and check global weather in real time",
            inline=False,
        )
        embed.set_footer(text="Type /help to explore all commands!")

        await interaction.response.send_message(embed=embed)
