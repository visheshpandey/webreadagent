#!/usr/bin/env python
"""CLI for the web research agent.

Usage:
    python research.py "your question here"
    python research.py "your question" --output report.md --sources 5
"""

import argparse
import sys

from dotenv import load_dotenv

from research_agent.agent import run


def main() -> int:
    parser = argparse.ArgumentParser(description="AI web research agent")
    parser.add_argument("question", help="The question or topic to research")
    parser.add_argument(
        "--output", "-o", help="Optional file path to also save the markdown report"
    )
    parser.add_argument(
        "--sources",
        "-s",
        type=int,
        default=4,
        help="Max search results to consider per query (default: 4)",
    )
    args = parser.parse_args()

    load_dotenv()

    try:
        report = run(args.question, sources_per_query=args.sources)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print()
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Saved report to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
