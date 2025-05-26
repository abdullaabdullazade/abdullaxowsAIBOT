import json
from prompt import format_prompt
from AI.ai_config import GEMINI_AI
from database.db import DatabaseManager
import requests
from datetime import datetime
import pytz
from logger_config import logger
from dotenv import load_dotenv
import os
from utils import async_wrap_blocking
import asyncio

load_dotenv()

BOT_NAME = os.getenv("BOT_NAME")


class TextAIHandler:
    """
    Handles all text-based AI interactions using the Gemini API,
    including generating replies, summarizing user history,
    providing facts, and filtering out irrelevant messages.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.timezone = ""

    async def generate_text_response(self, content: str, user_id: int) -> str:
        """
        Generates a smart text-based reply from the AI based on the user's input and history.

        Args:
            content (str): The user's latest message or question.
            user_id (int): Unique identifier for the user (from Discord).

        Returns:
            str: AI-generated reply to the user's message.
        """
        try:
            user_nickname = await self.db.get_user_nick(user_id)
            history = await self.db.get_recent_history(user_id)

            history_text = "\n".join(
                [f"{user_nickname}: {m}\n{BOT_NAME}: {r}" for m, r in history]
            )

            if not self.timezone:
                self.timezone = await self.get_server_timezone()

            clock = await self.get_current_time_in_timezone(self.timezone)

            prompt = format_prompt(
                template_name="text_response",
                BOT_NAME=BOT_NAME,
                history_text=history_text,
                content=content,
                nickname=user_nickname,
                time={clock},
                zone={self.timezone},
            )

            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=25,
            )
            full_response = response.text

            if full_response.count(".") >= 5:
                short_response = await self.get_ai_short_response(full_response)
            else:
                short_response = full_response

            await self.db.save_history(user_id, content, short_response)
            return full_response.strip()

        except Exception as e:
            logger.error(f"🚨 Error generating text response: {e}")
            return "I'm a bit confused. I'll get better. 😍"

    async def get_facts(self, user_id: int) -> str:
        """
        Retrieves a random factual or interesting message from the AI.

        Args:
            user_id (int): Discord user ID.

        Returns:
            str: A fun or educational fact provided by the AI.
        """
        try:
            tip_prompt = format_prompt("get_facts")
            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=tip_prompt),
                timeout=20,
            )
            tip_response = response.text
            short_response = await self.get_ai_short_response(tip_response)
            await self.db.save_history(user_id, "", short_response)
            return f"🧠 **Today's AI fact:**\n{tip_response.strip()}"
        except Exception:
            return "🤖 Oops! I couldn't find an AI fact at the moment. Please try again later 🌟📆"

    async def summarize_user_memory(self, user_id, nickname: str) -> str:
        """
        Summarizes all saved messages for a given user into a concise memory.

        Args:
            user_id (int): Discord user ID whose conversation history is being summarized.

        Returns:
            str: A summary of the user's memory, or a default message if empty.
        """
        full_text = await self.db.get_user_full_history(user_id)

        if not full_text.strip():
            return "I don't have anything about you in my memory. 😶"

        prompt = format_prompt("memory_prompt", prompt=full_text, nickname=nickname)
        try:
            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=20,
            )
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error summarizing memory: {e}")
            return "An error occurred while generating the summary."

    async def get_ai_short_response(self, response: str) -> str:
        """
        Generates a shorter or summarized version of a full AI response.

        Args:
            response (str): Full text response from the AI.

        Returns:
            str: A concise version of the AI response.
        """
        prompt = format_prompt("short_response", prompt=response)
        short_response = await asyncio.wait_for(
            async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
            timeout=20,
        )
        return short_response.text.strip()

    async def get_promptlab(self, prompt_text: str) -> str:
        """
        Enhances a given user prompt by transforming it into a vivid and imaginative
        image generation prompt using the Gemini AI model.

        Args:
            prompt_text (str): The raw input provided by the user describing a scene or idea.

        Returns:
            str: A refined and enriched prompt suitable for AI image generation.
                If an error occurs, returns a fallback error message.
        """
        prompt = format_prompt("photolab", prompt=prompt_text)
        try:
            result = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=20,
            )
            return result.text.strip()
        except Exception as e:
            logger.error(f"Error generationg prompt lab: {e}")
            return "An error occurred while generating the promptlab."

    async def delete_useless_messages(self, user_id: int) -> list:
        """
        Filters and removes messages from a user's history that are considered unimportant.

        Args:
            user_id (int): Discord user ID.

        Returns:
            list: A list of indices or identifiers of deleted messages.
        """
        text_user = await self.db.fetch_user_messages(user_id)
        if not text_user:
            return []

        prompt = format_prompt("useless_message", text_user=text_user)

        try:
            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=25,
            )
            json_response = json.loads(
                response.text.strip()[8:-3]
            )  # assume it returns '```json { ... }```'
            logger.info(json_response.get("delete", []))
            return json_response.get("delete", [])
        except Exception as e:
            logger.error(f"Error deleting useless messages: {e}")
            return []

    async def get_server_timezone(self) -> str:
        """
        Asynchronously retrieves the server's current timezone based on its IP address.

        Uses the ip-api.com service to determine geographical location and corresponding timezone.

        Returns:
            str: Timezone string in the format "Continent/City" (e.g., "Asia/Baku").
        """
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        return data.get("timezone", "UTC")

    async def get_current_time_in_timezone(self, timezone_str: str) -> str:
        """
        Returns the current date and time for the given timezone string.

        Args:
            timezone_str (str): Timezone name (e.g., "Asia/Baku").

        Returns:
            str: Formatted current time as 'YYYY-MM-DD HH:MM:SS'.
        """
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M:%S")
