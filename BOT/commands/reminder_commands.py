import discord
from discord.ext import commands
from discord import app_commands
from AI.text_ai import TextAIHandler
from BOT.handler import DiscordResponseHandler
from database.db import DatabaseManager
from datetime import datetime, timedelta
from BOT.reminder import ReminderHandler
from logger_config import logger


class ReminderCommands(commands.Cog):
    """
    Cog that handles reminder-related commands for a Discord bot.
    Allows users to add, list, and delete their reminders using slash commands.
    """

    def __init__(self, bot):
        """
        Initializes the ReminderCommands cog.

        Args:
            bot (commands.Bot): The bot instance to which this cog is attached.
        """
        self.bot = bot
        self.handler = DiscordResponseHandler()
        self.textai_handler = TextAIHandler()
        self.db = DatabaseManager()
        self.reminder_handler = ReminderHandler()

    @app_commands.command(
        name="remind_add", description="⏰ Add a reminder with timezone."
    )
    @app_commands.describe(
        day="Day of reminder",
        month="Month of reminder",
        year="Year of reminder",
        hour="Hour (LOCAL TIME)",
        minute="Minute (LOCAL TIME)",
        timezone_offset="Your UTC offset, example 4 or -5",
        message="Reminder message",
    )
    async def remind_add(
        self,
        interaction: discord.Interaction,
        day: int,
        month: int,
        year: int,
        hour: int,
        minute: int,
        timezone_offset: int,
        message: str,
    ):
        await interaction.response.defer(thinking=True)

        try:
            local_time = datetime(year, month, day, hour, minute)
        except ValueError as ve:
            logger.warning(f"⛔ Invalid datetime input: {ve}")
            await interaction.followup.send(
                f"❌ Invalid date or time provided: **{ve}**", ephemeral=True
            )
            return

        utc_time = local_time - timedelta(hours=timezone_offset)

        self.reminder_handler.add_reminder(
            interaction.user.id,
            reminder_datetime=utc_time,
            timezone_offset=timezone_offset,
            message=message,
        )

        nickname = interaction.user.display_name
        await self.handler.safe_embed_reply(
            interaction,
            f"✅ Reminder set!\n"
            f"🕒 Local time: **{local_time.strftime('%Y-%m-%d %H:%M')} (UTC{timezone_offset:+d})**\n"
            f"📩 Message: {message}",
            nickname,
            title="✨ Reminder Set",
        )

    @app_commands.command(
        name="remind_list", description="📋 List your active reminders."
    )
    async def remind_list(self, interaction: discord.Interaction):
        """
        Lists all active reminders for the user showing their local time.
        """
        reminders = self.reminder_handler.list_reminders_raw(interaction.user.id)
        if not reminders:
            await interaction.response.send_message(
                "📭 You have no active reminders.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🧠 Your Reminders (Local Time)", color=discord.Color.green()
        )
        for idx, reminder in enumerate(reminders):
            try:
                utc_dt = datetime.strptime(reminder["utc_date"], "%Y-%m-%d %H:%M")
                offset_hours = reminder.get("timezone_offset", 0)
                local_dt = utc_dt + timedelta(hours=offset_hours)
                local_dt_str = local_dt.strftime("%Y-%m-%d %H:%M")

                embed.add_field(
                    name=f"Reminder #{idx + 1}",
                    value=f"📅 Will trigger at: **{local_dt_str} (UTC{offset_hours:+d})**\n📝 Message: {reminder['message']}",
                    inline=False,
                )
            except Exception as e:
                logger.error(f"Error formatting reminder: {e}")

        embed.set_footer(text="Use /remind_delete <index> to delete a reminder.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="remind_delete", description="❌ Delete a reminder by its index."
    )
    @app_commands.describe(
        index="The index of the reminder to delete (from /remind_list)"
    )
    async def remind_delete(self, interaction: discord.Interaction, index: int):
        """
        Deletes a specific reminder based on its index in the user's reminder list.

        Args:
            interaction (discord.Interaction): The Discord interaction object.
            index (int): The 1-based index of the reminder to delete.
        """
        success = self.reminder_handler.delete_reminder(interaction.user.id, index - 1)
        if success:
            await interaction.response.send_message(
                f"🗑️ Reminder #{index} deleted!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Invalid reminder index.", ephemeral=True
            )
