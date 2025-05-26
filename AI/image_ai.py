from database.db import DatabaseManager
from prompt import format_prompt
from AI.ai_config import GEMINI_AI, GEMINI_IMAGE_AI
from uuid import uuid4
from PIL import Image
from io import BytesIO
from google.genai import types
from AI.text_ai import TextAIHandler
import asyncio
import os
from logger_config import logger
from dotenv import load_dotenv
from utils import async_wrap_blocking
from typing import Optional

load_dotenv()

BOT_NAME = os.getenv("BOT_NAME")


class ImageAIHandler:
    """Handles image generation and analysis using Gemini AI models."""

    def __init__(self):
        """Initializes database and text AI handlers."""
        self.db = DatabaseManager()
        self.textai_handler = TextAIHandler()

    async def generate_image(self, prompt_text: str, user_id: int) -> Optional[str]:
        """
        Generates an image based on user prompt.

        Args:
            prompt_text (str): Text describing the desired image.
            user_id (int): Discord user ID.

        Returns:
                Optional[str]: Path to the generated image file, or None if failed.
        """
        try:
            text_ = await self.render_image_prompt(prompt_text, user_id)

            try:
                response = await asyncio.wait_for(
                    async_wrap_blocking(
                        GEMINI_IMAGE_AI.models.generate_content,
                        model="gemini-2.0-flash-exp-image-generation",
                        contents=text_,
                        config=types.GenerateContentConfig(
                            response_modalities=["Text", "Image"]
                        ),
                    ),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                logger.error("⏰ Image generation timed out.")
                return None

            if not response.candidates:
                logger.error("❌ Gemini returned no image candidates.")
                return None

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image = Image.open(BytesIO(part.inline_data.data))
                    image_path = f"./media/out/{uuid4()}.png"
                    image.save(image_path)
                    await self.db.save_history(user_id, prompt_text, "")
                    return image_path

            logger.error("⚠️ Image part not found in the response.")
            return None

        except Exception as e:
            logger.error(f"🚨 Gemini error during image generation: {e}")
            return None

    async def get_analyze_image(
        self, path: str, prompt: str = "What describes on the photo?"
    ) -> str:
        """
        Analyzes an uploaded image and returns a text description.

        Args:
            path (str): Path to the image file.
            prompt (str, optional): Custom prompt for analysis.

        Returns:
            str: Analysis result or error message.
        """
        try:
            file_ref = await async_wrap_blocking(
                GEMINI_IMAGE_AI.files.upload, file=path
            )

            response = await async_wrap_blocking(
                GEMINI_IMAGE_AI.models.generate_content,
                model="gemini-2.0-flash", # gemini-1.5-flash
                contents=[prompt, file_ref],
            )

            logger.info(f"📷 Image analysis: {response.text}")
            return response.text

        except Exception as e:
            logger.error(f"🚨 Error analyzing image: {e}")
            os.remove(path)
            return "Error analyzing image."

    async def get_results_analyzing_image(
        self, prompt_text: str, user_id: int, content: str = ""
    ) -> str:
        """
        Sends image analysis results to Gemini and saves summary.

        Args:
            prompt_text (str): The prompt for analysis.
            user_id (int): Discord user ID.
            content (str, optional): Additional content.

        Returns:
            str: AI-generated analysis result.
        """
        try:
            user_nickname = await self.db.get_user_nick(user_id)

            prompt = format_prompt(
                "image_analyze_prompt",
                BOT_NAME=BOT_NAME,
                content=content,
                prompt=prompt_text,
                user_nickname=user_nickname,
            )

            response = await async_wrap_blocking(
                GEMINI_AI.generate_content, contents=prompt
            )
            short_response = await self.textai_handler.get_ai_short_response(response)
            await self.db.save_history(user_id, short_response, short_response)

            return response.text.strip()

        except Exception as e:
            logger.error(f"🚨 Error getting result analyzing image: {e}")
            return "Error analyzing image."

    async def check_image_requested(self, prompt_text: str, user_id: int) -> bool:
        """
        Checks if the user's prompt requests an image.

        Args:
            prompt_text (str): The prompt message.
            user_id (int): Discord user ID.

        Returns:
            bool: True if image generation is needed, False otherwise.
        """
        try:
            messages = await self.db.fetch_user_messages(user_id, 3)
            prompt = format_prompt(
                "image_request", messages=messages, prompt=prompt_text
            )
            result = await async_wrap_blocking(
                GEMINI_AI.generate_content, contents=prompt
            )

            logger.info(f"🤖 Image request decision: {result.text}")
            return "yes" in result.text.strip().lower()

        except Exception as e:
            logger.error(f"🚨 Image request check error: {e}")
            return False

    async def generate_image_text(self, prompt: str, success: bool = True) -> str:
        """
        Generates a response text after attempting image generation.

        Args:
            prompt (str): User prompt.
            success (bool, optional): Whether the image generation succeeded.

        Returns:
            str: Friendly success or failure message.
        """
        try:
            template_key = "image_success" if success else "image_failure"
            formatted_prompt = format_prompt(template_key, prompt=prompt)

            response = await async_wrap_blocking(
                GEMINI_AI.generate_content, contents=formatted_prompt
            )

            logger.info(f"🖼️ Image response: {response.text.strip()}")
            return response.text.strip()
        except Exception as e:
            logger.error(f"🚨 Error generating image text: {e}")
            return "Image generation is complete."

    async def render_image_prompt(self, text: str, user_id: int) -> str:
        """
        Builds a detailed image prompt based on user history and input.

        Args:
            text (str): Current prompt text.
            user_id (int): Discord user ID.

        Returns:
            str: Detailed image generation prompt.
        """
        try:
            history = await self.db.fetch_user_messages(user_id)
            history_text = "\n".join([f"- {msg}" for msg in history])

            prompt = format_prompt(
                "render_image_prompt", history_text=history_text, text=text
            )

            response = await async_wrap_blocking(
                GEMINI_AI.generate_content, contents=prompt
            )
            return response.text

        except Exception as e:
            logger.error(f"🚨 Error rendering image prompt: {e}")
            return text
