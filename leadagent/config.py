import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int) -> int:
    value = _get(name)
    return int(value) if value else default


GEMINI_API_KEY = _get("GEMINI_API_KEY")
GOOGLE_PLACES_API_KEY = _get("GOOGLE_PLACES_API_KEY")

AI_PROVIDER = _get("AI_PROVIDER", "gemini").lower()
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-flash-latest")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3.1")
OLLAMA_URL = _get("OLLAMA_URL", "http://localhost:11434")

YOUR_NAME = _get("YOUR_NAME", "Your Name")
BUSINESS_NAME = _get("BUSINESS_NAME")
SIGNATURE = f"{YOUR_NAME}, {BUSINESS_NAME}" if BUSINESS_NAME else YOUR_NAME
YOUR_PORTFOLIO = _get("YOUR_PORTFOLIO")
YOUR_SERVICES = _get("YOUR_SERVICES", "business websites")
PRICE_GUIDE = _get("PRICE_GUIDE")
MESSAGE_LANGUAGE = _get("MESSAGE_LANGUAGE", "English")

DEFAULT_CITY = _get("DEFAULT_CITY")
MIN_REVIEWS = _int("MIN_REVIEWS", 15)
MAX_REVIEWS = _int("MAX_REVIEWS", 3000)
DAILY_SEND_LIMIT = _int("DAILY_SEND_LIMIT", 20)

DB_PATH = ROOT / "leads.db"
