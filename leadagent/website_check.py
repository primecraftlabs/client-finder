"""Looks at a business's website and lists problems we could fix for them."""
import re
import time
from datetime import date
from urllib.parse import urlparse

import requests

SOCIAL_HOSTS = (
    "facebook.com", "instagram.com", "linktr.ee", "wa.me", "whatsapp.com",
    "justdial.com", "business.site", "sulekha.com", "indiamart.com", "youtube.com",
)
BOOKING_HINTS = ("book", "appointment", "wa.me", "api.whatsapp.com", "order online", "reserve", "schedule")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def check(url: str) -> dict:
    """Returns {"status": none|social_only|unreachable|ok, "issues": [...], "title": str}."""
    if not url:
        return {"status": "none", "issues": ["No website at all"], "title": ""}

    host = urlparse(url).netloc.lower()
    if any(s in host for s in SOCIAL_HOSTS):
        return {
            "status": "social_only",
            "issues": [f"Only has a social/directory page ({host}), no real website"],
            "title": "",
        }

    try:
        start = time.monotonic()
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        seconds = time.monotonic() - start
    except requests.RequestException:
        return {"status": "unreachable", "issues": ["Website does not open (broken or expired)"], "title": ""}

    if resp.status_code >= 400:
        return {
            "status": "unreachable",
            "issues": [f"Website returns an error (HTTP {resp.status_code})"],
            "title": "",
        }

    html = resp.text[:500_000]
    lower = html.lower()
    issues = []

    if not resp.url.startswith("https://"):
        issues.append("Not secure (no HTTPS) - browsers show a 'Not secure' warning")
    if not re.search(r"<meta[^>]+name\s*=\s*[\"']?viewport", lower):
        issues.append("Not mobile-friendly (no viewport tag) - most customers browse on phones")
    if seconds > 4:
        issues.append(f"Slow to load ({seconds:.1f}s)")
    if not any(hint in lower for hint in BOOKING_HINTS):
        issues.append("No online booking, ordering or WhatsApp button")
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(20\d{2})", lower)]
    if years and max(years) <= date.today().year - 3:
        issues.append(f"Looks outdated (copyright {max(years)})")

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip()[:150] if title_match else ""
    return {"status": "ok", "issues": issues, "title": title}
