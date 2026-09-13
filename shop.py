#!/usr/bin/env python
"""CLI for the shopping agent: researches a want, reads a live product catalog,
reasons about the best match, and takes a real action (adds to cart + checks out).

Usage:
    python shop.py "a durable backpack for daily commuting"
"""

import argparse
import sys

from dotenv import load_dotenv

from research_agent.shop_agent import run


def main() -> int:
    parser = argparse.ArgumentParser(description="AI shopping agent that reads, reasons, and acts")
    parser.add_argument("want", help="What you're looking to buy, in plain language")
    parser.add_argument("--first-name", default="Anakin")
    parser.add_argument("--last-name", default="Forge")
    parser.add_argument("--zip", default="94107")
    parser.add_argument("--screenshot", default="order_confirmation.png")
    parser.add_argument(
        "--headed", action="store_true",
        help="Show the real browser window instead of running headless (useful for screen recordings)",
    )
    parser.add_argument(
        "--slow-mo", type=int, default=300,
        help="Milliseconds to slow down each browser action by in --headed mode (default: 300)",
    )
    args = parser.parse_args()

    load_dotenv()

    try:
        result = run(
            args.want,
            buyer_first_name=args.first_name,
            buyer_last_name=args.last_name,
            buyer_zip=args.zip,
            screenshot_path=args.screenshot,
            headless=not args.headed,
            slow_mo_ms=args.slow_mo if args.headed else 0,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print()
    print(f"Want: {result['want']}")
    print(f"Chosen product: {result['chosen_product']} ({result['chosen_price']})")
    print(f"Reason: {result['reason']}")
    print(f"Order total: {result['order']['total']}")
    print(f"Confirmation: {result['order']['confirmation']}")
    print(f"Screenshot: {result['screenshot']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
