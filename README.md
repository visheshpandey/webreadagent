# Anakai — Read, Reason, Act Agents

Two AI agents built for the Anakin Forge hackathon, sharing a common "browse the live web + reason with an LLM" core, extended with a real browser-driven action.

## 1. Research agent (`research.py`)

Reads the live web, reasons through a question, and produces a synthesized, cited report.

1. Plans 2-4 targeted search queries for your question (Gemini).
2. Searches the web for each query (DuckDuckGo, free, no API key).
3. Fetches and reads the top results.
4. Synthesizes a cited answer from the collected content (Gemini).
5. Checks its own answer for gaps and, if needed, runs one more follow-up search before finalizing.

```bash
python research.py "What are the latest developments in solid-state batteries?"

# save to a file, and read more sources per query
python research.py "your question" --output report.md --sources 6
```

## 2. Shopping agent (`shop.py`)

Goes beyond research: it reads real market context from the web, reasons about the best matching product from a **live product catalog**, then **takes a real action** — adds the item to cart and completes checkout end-to-end via a real browser (Playwright), leaving a screenshot as proof.

1. Searches the live web for market context on what you want (price/feature research).
2. Logs into a live storefront and reads the current in-stock catalog (name, price, description).
3. Reasons about the single best match for your want, given the market context and catalog (Gemini).
4. Acts: drives a real browser to add the chosen product to cart and complete checkout, then saves a confirmation screenshot.

The demo storefront is [saucedemo.com](https://www.saucedemo.com/), built by Sauce Labs specifically for browser automation testing — real retailers (Amazon, etc.) aggressively block bots, which would make a live demo unreliable. No real payment or personal data is involved.

```bash
python shop.py "a durable backpack for daily commuting under 40 dollars"

# customize the checkout details and screenshot path
python shop.py "your want" --first-name Jane --last-name Doe --zip 10001 --screenshot proof.png
```

## Setup

```bash
pip install -r requirements.txt
python -m playwright install chromium   # only needed for shop.py
cp .env.example .env
# edit .env and set GEMINI_API_KEY=your-key-here
```

Get a free Gemini API key at https://aistudio.google.com/apikey

## Project layout

```
research_agent/
  search.py        # DuckDuckGo search (shared)
  fetch.py         # fetch + clean page text (shared)
  report.py        # markdown report formatting (research agent)
  agent.py         # research agent orchestration
  shop_browser.py  # Playwright automation against the live demo storefront
  shop_agent.py    # shopping agent orchestration (research -> reason -> act)
research.py        # research agent CLI
shop.py            # shopping agent CLI
```
