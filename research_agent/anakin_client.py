"""Client for Anakin's Search and URL Scraper APIs.

https://anakin.io/docs/api-reference/search/search
https://anakin.io/docs/api-reference/url-scraper/scrape
"""

import os

import requests

BASE_URL = "https://api.anakin.io/v1"
BROWSER_WS_URL = "wss://api.anakin.io/v1/browser-connect"
TIMEOUT_SECONDS = 30


def _api_key() -> str | None:
    return os.environ.get("ANAKIN_API_KEY")


def is_configured() -> bool:
    return bool(_api_key())


def browser_connect_options(record: bool = False) -> dict:
    """Connection options for Playwright's chromium.connect_over_cdp() to drive
    Anakin's managed cloud browser instead of a local one. Optionally records
    the session server-side as a WebM video (no extra cost)."""
    url = BROWSER_WS_URL + ("?record=true" if record else "")
    return {"ws_endpoint": url, "headers": {"X-API-Key": _api_key()}}


def list_recordings() -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/recordings",
        headers={"X-API-Key": _api_key()},
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("recordings", data if isinstance(data, list) else [])


def download_recording(recording_id: str, out_path: str) -> bool:
    resp = requests.get(
        f"{BASE_URL}/recordings/{recording_id}/download",
        headers={"X-API-Key": _api_key()},
        timeout=TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        return False
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return True


def search(query: str, limit: int = 5) -> list[dict]:
    """AI-powered web search via Anakin's Search API.

    Returns a list of {title, url, snippet} dicts, in the same shape as
    research_agent.search.search, so callers don't need to care which
    backend served the request.
    """
    resp = requests.post(
        f"{BASE_URL}/search",
        headers={"X-API-Key": _api_key(), "Content-Type": "application/json"},
        json={"prompt": query, "limit": limit},
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
        }
        for r in data.get("results", [])
    ]


def scrape(url: str, max_chars: int = 6000) -> str | None:
    """Fetch and clean a page's content via Anakin's inline URL Scraper.

    Uses Anakin's managed stealth browsers / anti-bot handling instead of a
    plain requests + BeautifulSoup fetch, so it can read JS-heavy pages that
    would otherwise fail. Returns None on failure or an incomplete job.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/url-scraper/scrape",
            headers={"X-API-Key": _api_key(), "Content-Type": "application/json"},
            json={"url": url},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    data = resp.json()
    if data.get("status") != "completed":
        return None

    markdown = data.get("markdown")
    if not markdown:
        return None

    return markdown[:max_chars]
