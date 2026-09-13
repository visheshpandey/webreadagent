"""Fetch a URL and extract readable text, preferring Anakin's managed URL
Scraper (handles JS-heavy pages and anti-bot measures) when configured,
falling back to a plain requests + BeautifulSoup fetch otherwise."""

import requests
from bs4 import BeautifulSoup

from . import anakin_client

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TIMEOUT_SECONDS = 10
MAX_CHARS_PER_PAGE = 6000


def _fetch_text_plain(url: str) -> str | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    if not text:
        return None

    return text[:MAX_CHARS_PER_PAGE]


def fetch_text(url: str) -> str | None:
    """Fetch a URL and return cleaned, truncated body text, or None on failure."""
    if anakin_client.is_configured():
        text = anakin_client.scrape(url, max_chars=MAX_CHARS_PER_PAGE)
        if text:
            return text
        # Fall through to the plain fetch if Anakin's job failed or timed out.
    return _fetch_text_plain(url)
