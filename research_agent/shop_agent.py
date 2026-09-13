"""Orchestrates the shopping agent: research a want, read the live catalog,
reason about the best match, then take a real action (buy it)."""

import os

from google import genai

from .search import search_many
from .fetch import fetch_text
from .shop_browser import Product, buy_product, list_products

MODEL_NAME = "gemini-3.6-flash"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


def _research_market_context(client: genai.Client, want: str, log) -> str:
    """Do a quick live web search for market context (typical prices/features)
    to help justify the pick with real-world grounding, reusing the research
    pipeline's search + fetch building blocks."""
    log(f"Researching market context for: {want}")
    results = search_many([f"best {want} price comparison"], max_results_per_query=3)
    excerpts = []
    for r in results[:3]:
        text = fetch_text(r["url"])
        if text:
            excerpts.append(f"{r['title']} ({r['url']}): {text[:1500]}")
    return "\n\n".join(excerpts) if excerpts else "No external market context found."


def _choose_product(client: genai.Client, want: str, market_context: str, products: list[Product]) -> tuple[Product, str]:
    catalog = "\n".join(
        f"- {p.name} | {p.price} | {p.description}" for p in products
    )
    prompt = (
        "You are a shopping assistant. A shopper wants: "
        f"\"{want}\".\n\n"
        f"Here is real-world market context from the live web:\n{market_context}\n\n"
        f"Here is the live in-stock catalog you can actually purchase from right now:\n{catalog}\n\n"
        "Pick the single best matching product from the catalog for this shopper, "
        "considering price and fit to their want. Reply in this exact format:\n"
        "PRODUCT: <exact product name from the catalog>\n"
        "REASON: <one or two sentence justification>"
    )
    resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = resp.text.strip()

    chosen_name = None
    reason = ""
    for line in text.splitlines():
        if line.upper().startswith("PRODUCT:"):
            chosen_name = line.split(":", 1)[1].strip()
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

    chosen = next((p for p in products if p.name == chosen_name), None)
    if chosen is None:
        # Fall back to a substring match in case the model paraphrased slightly.
        chosen = next((p for p in products if chosen_name and chosen_name.lower() in p.name.lower()), products[0])

    return chosen, reason or text


def run(want: str, buyer_first_name: str, buyer_last_name: str, buyer_zip: str,
        screenshot_path: str, log=print) -> dict:
    client = _get_client()

    market_context = _research_market_context(client, want, log)

    log("Reading live product catalog...")
    products = list_products(log=log)

    log("Reasoning about the best match...")
    chosen, reason = _choose_product(client, want, market_context, products)
    log(f"Chosen: {chosen.name} ({chosen.price}) -- {reason}")

    log("Taking action: adding to cart and completing checkout...")
    order = buy_product(
        chosen.name, buyer_first_name, buyer_last_name, buyer_zip,
        screenshot_path=screenshot_path, log=log,
    )

    return {
        "want": want,
        "chosen_product": chosen.name,
        "chosen_price": chosen.price,
        "reason": reason,
        "order": order,
        "screenshot": screenshot_path,
    }
