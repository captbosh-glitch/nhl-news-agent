"""
Optional: uses the Claude API to turn today's collected articles into a
short curated digest. Requires ANTHROPIC_API_KEY to be set in the
environment. If it's not set, main.py just skips this step.
"""

import os
from datetime import date

from config import ANTHROPIC_MODEL


def is_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def build_digest(articles):
    """
    articles: list of sqlite3.Row objects with title, source, summary, teams, url
    Returns a short curated digest as plain text.
    """
    if not articles:
        return None

    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    article_lines = []
    for a in articles:
        line = f"- [{a['source']}] {a['title']}"
        if a["teams"]:
            line += f" (teams: {a['teams']})"
        if a["summary"]:
            line += f"\n  {a['summary'][:300]}"
        article_lines.append(line)

    articles_block = "\n".join(article_lines)

    prompt = f"""You're curating a daily NHL news digest from today's raw article list below.

Write a concise digest (150-250 words) that:
- Leads with the most significant story or two (trades, injuries, standings shifts, big games)
- Groups related items where it makes sense
- Skips minor/duplicate stories
- Uses a neutral, informative tone -- no hype, no filler

Raw articles collected today:
{articles_block}

Return only the digest text, no preamble."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if block.type == "text")


def todays_date_str():
    return date.today().isoformat()
