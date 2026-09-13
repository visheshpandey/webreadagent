"""Assemble the final markdown report."""


def build_report(question: str, answer_markdown: str, sources: list[dict]) -> str:
    lines = [f"# Research Report: {question}", "", answer_markdown.strip(), "", "## Sources"]
    for i, src in enumerate(sources, start=1):
        title = src.get("title") or src["url"]
        lines.append(f"{i}. [{title}]({src['url']})")
    return "\n".join(lines) + "\n"
