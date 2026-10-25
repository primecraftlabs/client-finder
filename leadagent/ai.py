"""The AI brain. Swap providers with AI_PROVIDER in .env (gemini or ollama)."""
import time

import requests

from . import config


class AIError(Exception):
    pass


class GeminiBrain:
    """Gemini API free tier. Free limits are small (around 10 requests/minute), so calls are spaced out."""

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    MIN_SECONDS_BETWEEN_CALLS = 7

    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise AIError("GEMINI_API_KEY is missing in .env")
        self._last_call = 0.0

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        url = self.URL.format(model=config.GEMINI_MODEL)
        headers = {"x-goog-api-key": config.GEMINI_API_KEY}

        for attempt in range(4):
            wait = self.MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            resp = requests.post(url, json=body, headers=headers, timeout=60)
            if resp.status_code in (429, 500, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1))  # rate limited or overloaded: back off and retry
                continue
            if resp.status_code != 200:
                raise AIError(f"Gemini error {resp.status_code}: {resp.text[:500]}")
            try:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise AIError(f"Unexpected Gemini response: {resp.text[:500]}") from e
        raise AIError("Gemini kept rate-limiting; you may have hit today's free limit. Try again later.")

    @staticmethod
    def list_models() -> list[str]:
        resp = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            params={"pageSize": 1000},
            timeout=30,
        )
        if resp.status_code != 200:
            raise AIError(f"Gemini error {resp.status_code}: {resp.text[:500]}")
        return [
            m["name"].removeprefix("models/")
            for m in resp.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]


class OllamaBrain:
    """A model running locally with Ollama (https://ollama.com). Free and unlimited, but needs a strong PC."""

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        body = {"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if json_mode:
            body["format"] = "json"
        try:
            resp = requests.post(f"{config.OLLAMA_URL}/api/generate", json=body, timeout=300)
        except requests.ConnectionError as e:
            raise AIError("Can't reach Ollama. Is it installed and running?") from e
        if resp.status_code != 200:
            raise AIError(f"Ollama error {resp.status_code}: {resp.text[:500]}")
        return resp.json()["response"]


def get_brain():
    if config.AI_PROVIDER == "ollama":
        return OllamaBrain()
    if config.AI_PROVIDER == "gemini":
        return GeminiBrain()
    raise AIError(f"Unknown AI_PROVIDER '{config.AI_PROVIDER}' (use gemini or ollama)")
