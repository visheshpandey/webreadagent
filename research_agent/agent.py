"""Orchestrates the research agent: plan queries, search, read, synthesize, and
optionally follow up on gaps before producing a final cited report."""

import os
import re

from google import genai

from .fetch import fetch_text
from .report import build_report
from .search import search_many

MODEL_NAME = "gemini-3.1-flash-lite"
MAX_SOURCES_TO_READ = 8


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


def _generate(client: genai.Client, prompt: str) -> str:
    resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return resp.text


def _plan_queries(client: genai.Client, question: str) -> list[str]:
    prompt = (
        "You are a research planning assistant. Given the user's question, produce "
        "2 to 4 distinct, targeted web search queries that together would cover the "
        "different angles needed to answer it well. Reply with ONLY the queries, "
        "one per line, no numbering, no extra text.\n\n"
        f"Question: {question}"
    )
    text = _generate(client, prompt)
    queries = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
    return queries[:4] if queries else [question]


def _read_sources(log, results: list[dict], limit: int) -> list[dict]:
    read = []
    for r in results[:limit]:
        log(f"Reading: {r['url']}")
        text = fetch_text(r["url"])
        if text:
            r["content"] = text
            read.append(r)
        else:
            log(f"  (skipped, could not fetch)")
    return read


def _synthesize(client: genai.Client, question: str, sources: list[dict]) -> str:
    excerpts = []
    for i, s in enumerate(sources, start=1):
        excerpts.append(f"[{i}] {s['title']} ({s['url']})\n{s['content']}")
    context = "\n\n---\n\n".join(excerpts)

    prompt = (
        "You are a research analyst. Using ONLY the numbered source excerpts below, "
        "write a clear, well-organized answer to the question. Cite sources inline "
        "using their bracket numbers, e.g. [1], [2]. If sources disagree, note it. "
        "If the excerpts don't fully answer the question, say what's missing.\n\n"
        f"Question: {question}\n\n"
        f"Sources:\n{context}\n\n"
        "Write the answer now, in markdown, with inline citations."
    )
    return _generate(client, prompt)


def _find_gap_query(client: genai.Client, question: str, draft_answer: str) -> str | None:
    prompt = (
        "You just wrote this draft research answer. If it has a significant gap, "
        "missing angle, or unresolved contradiction that one more targeted web "
        "search could fix, reply with ONLY that single search query. "
        "If the answer is already sufficiently complete, reply with exactly: NONE.\n\n"
        f"Question: {question}\n\nDraft answer:\n{draft_answer}"
    )
    text = _generate(client, prompt).strip()
    if not text or text.upper() == "NONE":
        return None
    return re.sub(r"^[-*\d.\s]+", "", text.splitlines()[0]).strip()


def run(question: str, sources_per_query: int = 4, log=print) -> str:
    client = _get_client()

    log("Planning search queries...")
    queries = _plan_queries(client, question)
    for q in queries:
        log(f"  - {q}")

    log("Searching...")
    results = search_many(queries, max_results_per_query=sources_per_query)
    if not results:
        raise RuntimeError("No search results found.")

    log(f"Found {len(results)} candidate sources. Reading top {MAX_SOURCES_TO_READ}...")
    sources = _read_sources(log, results, MAX_SOURCES_TO_READ)
    if not sources:
        raise RuntimeError("Could not fetch content from any sources.")

    log("Synthesizing answer...")
    answer = _synthesize(client, question, sources)

    gap_query = _find_gap_query(client, question, answer)
    if gap_query:
        log(f"Identified a gap, running follow-up search: {gap_query}")
        follow_up_results = search_many([gap_query], max_results_per_query=sources_per_query)
        existing_urls = {s["url"] for s in sources}
        new_results = [r for r in follow_up_results if r["url"] not in existing_urls]
        new_sources = _read_sources(log, new_results, 3)
        if new_sources:
            sources.extend(new_sources)
            log("Re-synthesizing with additional sources...")
            answer = _synthesize(client, question, sources)

    return build_report(question, answer, sources)
