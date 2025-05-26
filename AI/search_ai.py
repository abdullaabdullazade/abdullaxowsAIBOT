import aiohttp
import asyncio
import random
import urllib.parse
from bs4 import BeautifulSoup
from database.db import DatabaseManager
from AI.text_ai import TextAIHandler
from prompt import format_prompt
from AI.ai_config import GEMINI_AI
from googlesearch import search
from logger_config import logger
import undetected_chromedriver as uc
from utils import async_wrap_blocking
from typing import List

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
]


class SmartGoogleSearcher:
    """Handles smart search queries, optimizations, and web content extraction using AI."""

    def __init__(self, max_results: int = 3):
        """Initializes SmartGoogleSearcher with database and AI handlers."""
        self.max_results = max_results
        self.db = DatabaseManager()
        self.textai_handler = TextAIHandler()

    async def optimize_query(self, query: str) -> str:
        """
        Optimizes a search query for better search results.

        Args:
            query (str): Raw user query.

        Returns:
            str: Optimized query string.
        """
        prompt = f"Optimize the following question into a clean, short search engine query:\n\n{query}\n\nResult:"
        try:
            optimized = await asyncio.wait_for(
                async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt),
                timeout=10,
            )
            return optimized.text.strip()
        except Exception as e:
            logger.error(f"🚨 Query optimization failed: {e}")
            return query

    async def google_search(self, query: str) -> List[str]:
        """
        Performs a Google search and retrieves a list of URLs.

        Args:
            query (str): Optimized search query.

        Returns:
            List[str]: List of result URLs.
        """
        results = []
        try:
            search_results = await async_wrap_blocking(
                search, query, num_results=self.max_results
            )
            for url in search_results:
                if url.startswith("http"):
                    results.append(url)
        except Exception as e:
            logger.warning(f"⚠️ Googlesearch failed, trying chromedriver: {e}")

        if not results:
            results = await self.google_search_with_chromedriver(query)

        return results

    async def google_search_with_chromedriver(self, query: str) -> List[str]:
        """
        Fallback search using undetected_chromedriver.

        Args:
            query (str): Search query.

        Returns:
            List[str]: List of found URLs.
        """
        results = []
        try:
            options = uc.ChromeOptions(version_main=136)
            options.add_argument("--headless")
            driver = await async_wrap_blocking(uc.Chrome, options=options)
            driver.get(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
            links = driver.find_elements("css selector", "div.yuRUbf > a")
            for link in links[: self.max_results]:
                href = link.get_attribute("href")
                if href and href.startswith("http"):
                    results.append(href)
            driver.quit()
        except Exception as e:
            logger.error(f"🚨 Chromedriver search error: {e}")
        return results

    async def bing_search(self, query: str) -> List[str]:
        """
        Performs a Bing search and retrieves a list of URLs.

        Args:
            query (str): Search query.

        Returns:
            List[str]: List of result URLs.
        """
        urls = []
        try:
            bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(bing_url, headers=headers, ssl=False) as resp:
                    text = await resp.text()
                    soup = BeautifulSoup(text, "html.parser")
                    links = soup.select("li.b_algo h2 a")
                    for link in links[:4]:
                        href = link.get("href")
                        if href and href.startswith("http"):
                            urls.append(href)
                        if len(urls) >= self.max_results:
                            break
        except Exception as e:
            logger.error(f"🚨 Bing search error: {e}")
        return urls

    async def fetch_page_content(self, url: str) -> str:
        """
        Fetches webpage content and extracts text from paragraphs.

        Args:
            url (str): URL of the webpage.

        Returns:
            str: Extracted text content (up to 1500 characters).
        """
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        if any(
            x in url
            for x in [".pdf", "instagram.com", "twitter.com", "youtube.com", "youtu.be"]
        ):
            return f"🔗 Link: {url}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=5, ssl=False
                ) as resp:
                    if resp.status != 200:
                        return ""
                    try:
                        text = await resp.text()
                    except UnicodeDecodeError:
                        text = await resp.text(encoding="latin1")
                    soup = BeautifulSoup(text, "html.parser")
                    paragraphs = soup.find_all("p")
                    content = " ".join(p.get_text() for p in paragraphs)
                    return content[:1500]
        except Exception as e:
            logger.error(f"🚨 Fetch page content error: {e}")
            return ""

    async def smart_search_response(self, user_id: int, query: str) -> str:
        """
        Orchestrates the smart search workflow:
        optimizes query, fetches search results, retrieves page contents,
        summarizes, and returns a clean final AI response.

        Args:
            user_id (int): Discord user ID.
            query (str): Original search query.

        Returns:
            str: Final AI-generated smart search response.
        """
        try:
            optimized_query = await self.optimize_query(query)

            google_task = asyncio.create_task(self.google_search(optimized_query))
            bing_task = asyncio.create_task(self.bing_search(optimized_query))

            google_urls, bing_urls = await asyncio.gather(google_task, bing_task)
            all_urls = list(dict.fromkeys(google_urls + bing_urls))[
                : self.max_results * 2
            ]

            if not all_urls:
                return "No results found."

            fetch_tasks = [self.fetch_page_content(url) for url in all_urls]
            page_contents = await asyncio.gather(*fetch_tasks)

            combined_summary = "\n\n".join(
                [content for content in page_contents if content]
            )
            combined_summary = (
                combined_summary[:4000]
                if combined_summary
                else "No useful content found."
            )

            nickname = await self.db.get_user_nick(user_id)

            prompt_ = format_prompt(
                "search_prompt",
                results=combined_summary,
                nickname=nickname,
                query=query,
            )
            try:
                response = await asyncio.wait_for(
                    async_wrap_blocking(GEMINI_AI.generate_content, contents=prompt_),
                    timeout=25,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "⏰ Gemini content generation timeout during smart search."
                )
                return "⏰ Search summary generation timed out."

            short_response = await self.textai_handler.get_ai_short_response(response)
            await self.db.save_history(user_id, query, short_response)

            return response.text.strip()

        except Exception as e:
            logger.error(f"🚨 Smart search process failed: {e}")
            return "🚨 Smart search failed."
