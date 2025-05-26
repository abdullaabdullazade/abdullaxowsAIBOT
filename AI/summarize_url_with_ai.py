from AI.text_ai import TextAIHandler
from utils import async_wrap_blocking
from AI.ai_config import GEMINI_AI
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from prompt import format_prompt
from database.db import DatabaseManager
from logger_config import logger
import asyncio


class SummarizeURL:
    def __init__(self):
        """Initializes the SummarizeURL class."""
        self.textai_handler = TextAIHandler()
        self.db = DatabaseManager()

    async def summarize_url(self, url: str, user_id: int) -> str:
        """
        Extracts and summarizes the main content from a given webpage URL using AI.

        This function uses a headless browser (undetected_chromedriver) to load the webpage,
        extracts visible text (especially from <p> tags), and sends the content to a language model
        to generate a concise summary. The final result is stored in the user's history.

        Args:
            url (str): The URL of the webpage to summarize.
            user_id (int): The ID of the user requesting the summary.

        Returns:
            str: A short, natural summary of the webpage content or an error message if failed.
        """
        try:
            options = uc.ChromeOptions()
            options.add_argument("--headless")
            driver = uc.Chrome(options=options)
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url

            driver.get(url)
            await asyncio.sleep(3)

            html = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html, "html.parser")
            paragraphs = soup.find_all("p")
            content = " ".join(p.get_text() for p in paragraphs)
            content = content.strip()[:3000]

            if not content:
                return "❌ No content found on the page."

            prompt_ = format_prompt(
                "summarize_url_prompt",
                content=content,
            )

            ai_response = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, prompt_), timeout=25
            )
            short_response = await self.textai_handler.get_ai_short_response(
                ai_response
            )

            await self.db.save_history(user_id, url, short_response)
            return ai_response.text.strip()

        except Exception as e:
            logger.error(f"Error during summarize_url: {e}")
            return "❌ An error occurred while summarizing the URL."
