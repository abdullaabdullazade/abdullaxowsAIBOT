from AI.ai_config import GEMINI_AI
from database.db import DatabaseManager
from AI.text_ai import TextAIHandler
from prompt import format_prompt
import fitz
import os
import docx
import pandas as pd
from logger_config import logger
from utils import async_wrap_blocking
import asyncio
import aiofiles

class DocAIHandler:
    """Handles document reading, analysis, and summarization via Gemini AI."""

    def __init__(self):
        """Initializes database and text AI handlers."""
        self.db = DatabaseManager()
        self.textai_handler = TextAIHandler()

    async def read_file_async(self, file_path: str) -> str:
        """
        Asynchronously reads and extracts text from a supported file.

        Args:
            file_path (str): Path to the document.

        Returns:
            str: Extracted text content.

        Raises:
            ValueError: If the file format is unsupported.
        """
        if file_path.endswith(".pdf"):
            doc = await async_wrap_blocking(fitz.open, file_path)
            return "\n".join([page.get_text() for page in doc])

        elif file_path.endswith(".docx"):
            doc = await async_wrap_blocking(docx.Document, file_path)
            return "\n".join([para.text for para in doc.paragraphs])

        elif file_path.endswith(".csv"):
            df = await async_wrap_blocking(pd.read_csv, file_path)
            return df.to_string(index=False)

        elif file_path.endswith(".xlsx"):
            df = await async_wrap_blocking(pd.read_excel, file_path)
            return df.to_string(index=False)

        else:
            try:
                async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                    return await f.read()
            except Exception as e:
                logger.error(f"❌ Unsupported file format: {e}")
                raise ValueError("Unsupported file format.")

    async def analyze_document(
        self, file_path: str, user_id: int, prompt: str = "Summarize this document"
    ) -> str:
        """
        Analyzes the content of a document and generates a summarized response.

        Args:
            file_path (str): Path to the document.
            user_id (int): Discord user ID.
            prompt (str, optional): Custom analysis prompt.

        Returns:
            str: AI-generated summary or an error message.
        """
        try:
            try:
                file_text = await self.read_file_async(file_path)
            except ValueError:
                os.remove(file_path)
                return "❌ Unsupported file format."

            prompt_ = format_prompt("docs_prompt", prompt=prompt)
            ai_input = f"{prompt_}\n\n{file_text[:100000]}"

            try:
                response = await asyncio.wait_for(
                    async_wrap_blocking(GEMINI_AI.generate_content, contents=ai_input),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                logger.error("⏰ Document analysis timed out.")
                return "⏰ Document analysis timed out."

            short_response = await self.textai_handler.get_ai_short_response(response)
            await self.db.save_history(user_id, prompt, short_response)

            return response.text.strip()

        except Exception as e:
            logger.error(f"❌ Error analyzing document: {e}")
            return "❌ Failed to analyze document."
