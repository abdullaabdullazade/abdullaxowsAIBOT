"""
It sets up:
- Gemini (Google Generative AI) for text generation and image generation
- Groq (Whisper)
- API keys are securely imported from the .env file.
"""


import google.generativeai as gen_ai
from groq import Groq
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()


# GET API KEYS FROM .ENV
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


#CONFIGURATION

gen_ai.configure(api_key=GEMINI_API_KEY)

GEMINI_AI = gen_ai.GenerativeModel("gemini-2.0-flash")

GEMINI_IMAGE_AI = genai.Client(api_key=GEMINI_API_KEY)

GROQ = Groq(api_key=GROQ_API_KEY)