import json
import os
import asyncio
from datetime import datetime
from BOT.handler import DiscordResponseHandler
from logger_config import logger


class ReminderHandler:
    """
    A handler class for managing user reminders.

    Reminders are stored in a JSON file and can be added, listed, deleted,
    and automatically triggered at the appropriate UTC time.
    """

    def __init__(self, file_path="reminders.json"):
        self.file_path = file_path
        self.reminders = self.load_reminders()
        self.handler = DiscordResponseHandler()

    def load_reminders(self) -> dict:
        """
        Loads reminders from the JSON file.

        Returns:
            dict: A dictionary where keys are user IDs and values are lists of reminders.
        """
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_reminders(self) -> None:
        """
        Saves the current reminders to the JSON file.
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.reminders, f, indent=4, ensure_ascii=False)

    def add_reminder(
        self,
        user_id: int,
        reminder_datetime: datetime,
        timezone_offset: int,
        message: str,
    ) -> None:
        """
        Adds a new reminder for a user.

        Args:
            user_id (int): The Discord user ID.
            reminder_datetime (datetime): The UTC datetime when the reminder should trigger.
            timezone_offset (int): The timezone offset of the user (e.g., +4, -5).
            message (str): The reminder message.
        """
        user_id = str(user_id)
        if user_id not in self.reminders:
            self.reminders[user_id] = []
        self.reminders[user_id].append(
            {
                "utc_date": reminder_datetime.strftime("%Y-%m-%d %H:%M"),
                "timezone_offset": timezone_offset,
                "message": message,
            }
        )
        self.save_reminders()

    def list_reminders_raw(self, user_id: int) -> list:
        """
        Lists all active reminders for a user in raw dictionary form.

        Args:
            user_id (int): The Discord user ID.

        Returns:
            list: List of reminders as dictionaries.
        """
        user_id = str(user_id)
        reminders = self.load_reminders()
        return reminders.get(user_id, [])

    def delete_reminder(self, user_id: int, index: int) -> bool:
        """
        Deletes a specific reminder based on its index.

        Args:
            user_id (int): The Discord user ID.
            index (int): The index of the reminder to delete (0-based).

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        user_id = str(user_id)
        if user_id in self.reminders and 0 <= index < len(self.reminders[user_id]):
            del self.reminders[user_id][index]
            self.save_reminders()
            return True
        return False

    def list_reminders_raw(self, user_id: int) -> list:
        """
        Lists all active reminders for a user in raw dictionary form.

        Args:
            user_id (int): The Discord user ID.

        Returns:
            list: List of reminders as dictionaries.
        """
        user_id = str(user_id)
        self.load_reminders()
        return self.reminders.get(user_id, [])

    async def reminder_loop(self, bot) -> None:
        """
        Background task that continuously checks and sends reminders at the correct UTC time.

        Args:
            bot (commands.Bot): The running Discord bot instance.
        """
        while True:
            self.reminders = self.load_reminders()
            now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            to_delete = []

            for user_id, reminder_list in self.reminders.items():
                for reminder in reminder_list:
                    if reminder["utc_date"] == now_utc:
                        user = await bot.fetch_user(int(user_id))
                        if user:
                            try:
                                await self.handler.safe_embed_reply(
                                    user,
                                    f"{reminder['message']}",
                                    nickname=user.name,
                                    title="🔔 Reminder:",
                                    reminder=True,
                                )
                            except Exception as e:
                                logger.error(f"Failed to send reminder: {e}")
                        to_delete.append((user_id, reminder))

            for user_id, reminder in to_delete:
                if reminder in self.reminders.get(user_id, []):
                    self.reminders[user_id].remove(reminder)
            if to_delete:
                self.save_reminders()

            await asyncio.sleep(30)
