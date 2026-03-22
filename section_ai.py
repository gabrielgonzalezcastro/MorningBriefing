# ─── AI SECTION ────────────────────────────────────────────────────────────────
# Everything related to the Artificial Intelligence section:
# constants, feed fetching, and HTML building.

from sources import AI_FEEDS, AI_DEV_FEEDS
from events import fetch_dublin_ai_events

MAX_AI     = 10
MAX_AI_DEV = 5


def fetch_ai_entries(fetch_entries_fn):
    """Fetch AI top stories and AI dev articles. Returns (ai_entries, ai_dev_entries)."""
    ai_entries     = fetch_entries_fn(AI_FEEDS,     MAX_AI)
    ai_dev_entries = fetch_entries_fn(AI_DEV_FEEDS, MAX_AI_DEV)
    return ai_entries, ai_dev_entries


def build_ai_section(ai_entries, ai_dev_entries,
                     build_card, build_subsection, build_event_card, build_section):
    """Build and return the full HTML for the AI section."""
    body = build_subsection("Top Stories")
    body += "\n".join(
        build_card(e, "highlight-ai" if i == 0 else "")
        for i, e in enumerate(ai_entries)
    )

    if ai_dev_entries:
        body += "\n" + build_subsection("AI &amp; Software Development")
        body += "\n".join(build_card(e) for e in ai_dev_entries)

    dublin_ai_events = fetch_dublin_ai_events()
    if dublin_ai_events:
        body += "\n" + build_subsection("Dublin Events")
        body += "\n".join(
            build_event_card(e, i == 0)
            for i, e in enumerate(dublin_ai_events)
        )

    return build_section(
        "ai", "&#x1F9E0;", "ai-title",
        "Artificial Intelligence", "sec-ai",
        body
    )
