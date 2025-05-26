import random
from uuid import uuid4
import aiohttp
import asyncio
import edge_tts
from prompt import format_prompt
from AI.ai_config import GEMINI_AI, GROQ
from logger_config import logger
from utils import async_wrap_blocking
from typing import Optional


class VoiceAIHandler:
    """Handles voice transcription, voice detection, and text-to-speech generation."""

    WHISPER_MODELS = [
        "whisper-large-v3-turbo",
    ]

    def __init__(self):
        """Initializes audio storage folder."""
        self.audio_folder = "media/audio"

    async def transcribe_with_groq_whisper(self, audio_url: str) -> Optional[str]:
        """
        Transcribes audio from a given URL using Groq Whisper model.

        Args:
            audio_url (str): Public URL of the audio file.

        Returns:
            Optional[str]: Transcribed text, or None if failed.
        """
        try:
            file_path = f"{self.audio_folder}/{uuid4().hex}.mp3"

            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error("❌ Error downloading voice message.")
                        return None
                    content = await resp.read()

            await self.save_to_file(file_path, content)

            transcription = await self.transcribe_audio_file(file_path)

            return transcription.text.strip() if transcription else None

        except Exception as e:
            logger.error(f"🚨 Transcription error: {e}")
            return None

    async def save_to_file(self, file_path: str, content: bytes) -> None:
        """
        Saves binary content to a file.

        Args:
            file_path (str): Destination file path.
            content (bytes): File content to write.
        """
        with open(file_path, "wb") as f:
            f.write(content)

    async def transcribe_audio_file(self, file_path: str):
        """
        Transcribes audio file using Groq Whisper.

        Args:
            file_path (str): Path to the audio file.

        Returns:
            Transcription object.
        """
        with open(file_path, "rb") as audio_file:
            return GROQ.audio.transcriptions.create(
                file=audio_file,
                model=random.choice(self.WHISPER_MODELS),
                language="en",
                prompt="This is English voice.",
                response_format="json",
                temperature=0.0,
            )

    async def detect_voice(self, text: str) -> str:
        """
        Detects appropriate TTS voice model based on input text.

        Args:
            text (str): Input text.

        Returns:
            str: Detected voice model name.
        """
        try:
            prompt = format_prompt("detect_voice", prompt=text)

            response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=20,
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"🚨 Error detecting voice: {e}")
            return "en-US-JennyNeural"

    async def text_to_speech(self, text: str) -> str:
        """
        Converts text to speech and saves as an OGG file.

        Args:
            text (str): Text to convert.

        Returns:
            str: Path to generated .ogg audio file.
        """
        filename_base = f"{self.audio_folder}/{uuid4()}"
        try:
            lang_model = await self.detect_voice(text)
            communicate = edge_tts.Communicate(text, voice=lang_model)
            await communicate.save(f"{filename_base}.ogg")

        except Exception as e:
            logger.error(f"🚨 Error in TTS generation, fallback: {e}")
            lang_model = "en-US-JennyNeural"
            communicate = edge_tts.Communicate(text, voice=lang_model)
            await communicate.save(f"{filename_base}.ogg")

        logger.info(f"🔊 Audio generated: {filename_base}.ogg")
        return f"{filename_base}.ogg"
