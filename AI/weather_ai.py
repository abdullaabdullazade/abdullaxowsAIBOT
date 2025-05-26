import aiohttp
import os
from dotenv import load_dotenv
from logger_config import logger

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


class Weather:
    """Service for fetching weather data from the OpenWeatherMap API."""

    def __init__(self):
        """Initializes the Weather service with API key and base URL."""
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    async def fetch_weather(self, city) -> dict:
        """
        Fetch current weather information for a given city.

        Args:
            city (str): The name of the city to search weather for.

        Returns:
            dict or None: Weather data dictionary if successful, otherwise None.
        """
        params = {"q": city, "appid": self.api_key, "units": "metric", "lang": "en"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, params=params, timeout=10
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return None
