"""Web search, preferring Anakin's AI-powered Search API when configured,
falling back to DuckDuckGo (free, no API key) otherwise."""

from . import anakin_client

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )
    return results


def search(query: str, max_results: int = 5) -> list[dict]:
    """Run a search and return a list of {title, url, snippet} dicts."""
    if anakin_client.is_configured():
        return anakin_client.search(query, limit=max_results)
    return _search_duckduckgo(query, max_results=max_results)


def search_many(queries: list[str], max_results_per_query: int = 5) -> list[dict]:
    """Run several queries and return deduplicated results (by URL), tagged with the query that found them."""
    seen_urls = set()
    combined = []
    for q in queries:
        for r in search(q, max_results=max_results_per_query):
            url = r["url"]
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            r["query"] = q
            combined.append(r)
    return combined
