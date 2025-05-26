import aiofiles
from uuid import uuid4
import os
import requests
import base64
import random
import discord
from BOT.bot_config import BOT_NAME, DISCORD_BOT_TOKEN
from AI.voice_ai import VoiceAIHandler
from AI.image_ai import ImageAIHandler
from AI.text_ai import TextAIHandler
from database.db import DatabaseManager
from logger_config import logger
from AI.doc_ai import DocAIHandler
from utils import async_wrap_blocking
import asyncio
from typing import Optional, Union


class DiscordResponseHandler:
    """
    Main handler for processing and responding to different types of Discord user inputs:
    text, image, and audio. Integrates AI modules for text generation, image analysis,
    and voice transcription/synthesis.
    """

    DISCORD_EMBED_LIMIT = 3900

    def __init__(self):
        self.bot_token = DISCORD_BOT_TOKEN
        self.db = DatabaseManager()
        self.textai_handler = TextAIHandler()
        self.imageai_handler = ImageAIHandler()
        self.voiceai_handler = VoiceAIHandler()
        self.docai = DocAIHandler()

    @staticmethod
    def check_image(file: discord.Attachment) -> bool:
        """
        Checks if uploaded file is an image (png, jpg, jpeg).

        Args:
            file (discord.Attachment): Uploaded file from the message.

        Returns:
            bool: True if it's an image file, otherwise False.
        """
        return any(
            file.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]
        )

    async def image_mode(
        self, message: discord.Message, user_id: Union[int, str], content: str
    ) -> str:
        """
        Handles image generation requests. Generates an image based on the user's prompt
        and sends it back as a reply.
        Parameters:
            message (discord.Message): The original Discord message object to reply to.
            user_id (int or str): Unique identifier for the user who sent the prompt.
            content (str): The textual prompt to generate the image from.

        Returns:
            str: The reply message that was sent (with or without an image).
        """
        image_path, reply_msg = await self.generate_imagine_response(content, user_id)
        if image_path:
            file = discord.File(image_path)
            await message.reply(content=reply_msg, file=file)
            await async_wrap_blocking(os.remove, image_path)
        else:
            await message.reply(content=reply_msg)
        return reply_msg

    async def process_text_message(
        self,
        message: discord.Message,
        user_id: str,
        user_message_type: str,
        channel_id: int,
        content: str,
    ) -> None:
        """
        Processes a plain text message or image-generation text command.

        Args:
            message (discord.Message): The received Discord message object.
            user_id (str): ID of the message sender.
            user_message_type (str): Type of message (e.g., 'text' or 'image').
            channel_id (int): Channel where the message was sent.
            content (str): Text content of the message.
        """
        try:
            await message.channel.typing()
            if user_message_type == "image":
                await self.image_mode(message, user_id, content)
            else:
                reply_msg = await self.textai_handler.generate_text_response(
                    content, user_id
                )
                await self.handle_text_or_voice_response(
                    message, reply_msg, user_message_type, channel_id
                )
            await self.db.success_response(user_id)

        except Exception as e:
            logger.error(e)

    async def process_image_attachment(
        self,
        message: discord.Message,
        file: discord.Attachment,
        content: str,
        user_id: str,
        user_message_type: str,
        channel_id: int,
    ) -> None:
        """
        Handles image uploads: saves image, analyzes it with AI, and optionally generates new images.

        Args:
            message (discord.Message): Message object.
            file (discord.Attachment): Image attachment.
            content (str): Prompt text.
            user_id (str): Discord user ID.
            user_message_type (str): 'text' or 'image'.
            channel_id (int): Discord channel ID.
        """
        image_path = await self.save_image(file)
        try:
            if user_message_type == "image":
                analyzing_image = await self.imageai_handler.get_analyze_image(
                    image_path
                )
                await self.image_mode(message, user_id, analyzing_image + content)
            else:
                analyzing_image = (
                    await self.imageai_handler.get_analyze_image(image_path, content)
                    if content
                    else await self.imageai_handler.get_analyze_image(image_path)
                )
                reply_msg = await self.imageai_handler.get_results_analyzing_image(
                    analyzing_image, user_id, content
                )
                await self.handle_text_or_voice_response(
                    message, reply_msg, user_message_type, channel_id
                )
            await self.db.success_response(user_id)
        finally:
            await async_wrap_blocking(os.remove, image_path)

    async def process_audio_attachment(
        self,
        message: discord.Message,
        file: discord.Attachment,
        user_id: str,
        user_message_type: str,
        channel_id: int,
    ) -> None:
        """
        Processes an audio message by transcribing it, generating a reply, and responding via text or voice.

        Args:
            message (discord.Message): Discord message object.
            file (discord.Attachment): Audio file.
            user_id (str): User ID.
            user_message_type (str): Message type.
            channel_id (int): Channel ID.
        """

        transcript = await self.voiceai_handler.transcribe_with_groq_whisper(file.url)
        if not transcript:
            await message.reply(
                "I'm sorry, I couldn't quite catch your voice. Would you mind sending it again, please? 😔"
            )
            return

        if user_message_type == "image":
            reply_msg = await self.image_mode(message, user_id, transcript)

        else:
            reply_msg = await self.textai_handler.generate_text_response(
                transcript, user_id
            )
            await self.handle_text_or_voice_response(
                message, reply_msg, user_message_type, channel_id
            )
        await self.db.save_history(user_id, transcript, reply_msg)
        await self.db.success_response(user_id)

    async def analyze_document(
        self,
        message: discord.Message,
        user_message_type: str,
        file: str,
        user_id: str,
        channel_id: int,
        content: Optional[str],
    ) -> None:
        if user_message_type == "image":
            await self.safe_embed_reply(
                message,
                "Oops! 📷 I’m in image mode right now and can’t analyze documents this way.",
                message.author.display_name,
            )
            return

        if content:
            reply_msg = await self.docai.analyze_document(
                file_path=file, user_id=user_id, prompt=content
            )
        else:
            reply_msg = await self.docai.analyze_document(
                file_path=file, user_id=user_id, prompt=content
            )
        logger.info(reply_msg)
        await self.handle_text_or_voice_response(
            message, reply_msg, user_message_type, channel_id
        )

    async def handle_text_or_voice_response(
        self,
        message: discord.Message,
        reply_msg: str,
        user_message_type: str,
        channel_id: int,
    ) -> None:
        """
        Handles the dispatch of either text or voice responses.

        Args:
            message (discord.Message): Message object.
            reply_msg (str): The generated response text.
            user_message_type (str): 'text' or 'voice'.
            channel_id (int): Channel ID for voice response.
        """
        if user_message_type == "text":
            await self.safe_embed_reply(message, reply_msg, message.author.display_name)
        else:
            voice_message_path = await self.voiceai_handler.text_to_speech(reply_msg)
            await self.send_voice_message_to_discord(
                voice_message_path, channel_id, message.id
            )

    async def generate_imagine_response(
        self, prompt: str, user_id: str
    ) -> tuple[Optional[str], str]:
        """
        Generates an image and response message based on the given prompt and user ID.

        Args:
            prompt (str): The text prompt describing the image.
            user_id (str): The Discord user ID who initiated the request.

        Returns:
            Tuple[str or None, str]: (image_path, reply_text)
        """
        image_path = await self.imageai_handler.generate_image(
            prompt_text=prompt, user_id=user_id
        )
        reply_text = await self.imageai_handler.generate_image_text(
            prompt=prompt, success=bool(image_path)
        )
        return image_path, reply_text

    async def safe_embed_reply(
        self,
        target: Union[discord.Message, discord.Interaction],
        full_text: str,
        nickname: str,
        title: str = f"💬 Response - {BOT_NAME}",
        reminder: bool = False,
    ) -> None:
        """
        Sends a chunked and styled Discord embed or plain message based on content size.

        Args:
            target: discord.Message or discord.Interaction
            full_text (str): Full reply message.
            nickname (str): Display name of the user.
            title (str): Title of the embed message.
        """
        chunks = [
            full_text[i : i + self.DISCORD_EMBED_LIMIT]
            for i in range(0, len(full_text), self.DISCORD_EMBED_LIMIT)
        ]
        is_interaction = isinstance(target, discord.Interaction)
        if reminder:
            send_func = target.send
        else:
            send_func = target.followup.send if is_interaction else target.reply

        for idx, chunk in enumerate(chunks):
            try:
                embed = discord.Embed(
                    title=title if idx == 0 else None,
                    description=chunk,
                    color=discord.Color(random.randint(0, 0xFFFFFF)),
                )
                if idx == 0:
                    embed.set_footer(text=f"Response for {nickname}")
                await send_func(embed=embed)
            except Exception as e:
                logger.error(f"Embed failed, using plain text: {e}")
                for text_part in [
                    chunk[i : i + self.DISCORD_EMBED_LIMIT]
                    for i in range(0, len(chunk), self.DISCORD_EMBED_LIMIT)
                ]:
                    await send_func(content=text_part)

    async def save_image(self, file: discord.Attachment) -> str:
        """
        Saves uploaded image file locally.

        Args:
            file (discord.Attachment): Image file to save.

        Returns:
            str: Path to the saved image.
        """
        image_bytes = await file.read()
        filename = f"{uuid4()}.jpg"
        image_path = os.path.join("media/images", filename)
        async with aiofiles.open(image_path, "wb") as f:
            await f.write(image_bytes)
        return image_path

    async def save_document(self, file: discord.Attachment) -> str:
        """
        Saves uploaded file (image, PDF, DOC, etc.) locally.

        Args:
            file (discord.Attachment): File to save.

        Returns:
            str: Path to the saved file.
        """
        file_bytes = await file.read()

        _, ext = os.path.splitext(file.filename)
        ext = ext.lower() if ext else ".bin"

        filename = f"{uuid4()}{ext}"
        save_dir = "media/files"
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)

        return file_path

    async def send_voice_message_to_discord(
        self, ogg_path: str, channel_id: int, reply_to_message_id: Optional[int] = None
    ) -> None:
        """
        Sends a voice message (OGG) to Discord via raw API upload.

        Args:
            ogg_path (str): Path to the OGG voice file.
            channel_id (int): ID of the channel to send to.
            reply_to_message_id (int, optional): Message ID to reply to.
        """
        file_size = os.path.getsize(ogg_path)

        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

        json_data = {
            "files": [
                {"filename": "voice-message.ogg", "file_size": file_size, "id": "0"}
            ]
        }

        res = await asyncio.to_thread(
            requests.post,
            f"https://discord.com/api/v10/channels/{channel_id}/attachments",
            headers=headers,
            json=json_data,
        )
        res.raise_for_status()
        upload_data = res.json()["attachments"][0]

        with open(ogg_path, "rb") as f:
            audio_bytes = f.read()

        await asyncio.to_thread(
            requests.put,
            upload_data["upload_url"],
            headers={"Content-Type": "audio/ogg"},
            data=audio_bytes,
        )

        waveform = [random.randint(0, 255) for _ in range(256)]
        waveform_b64 = base64.b64encode(bytes(waveform)).decode()

        voice_json = {
            "flags": 8192,
            "attachments": [
                {
                    "id": "0",
                    "filename": "voice-message.ogg",
                    "uploaded_filename": upload_data["upload_filename"],
                    "duration_secs": 10,
                    "waveform": waveform_b64,
                }
            ],
        }

        if reply_to_message_id:
            voice_json["message_reference"] = {
                "message_id": reply_to_message_id,
                "channel_id": channel_id,
            }

        await asyncio.to_thread(
            requests.post,
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json=voice_json,
        )

        logger.info(f"✅ Voice message sent successfully: {ogg_path}")
        await async_wrap_blocking(os.remove, ogg_path)
