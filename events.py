# ─── DYNAMIC DUBLIN EVENT FETCHING ─────────────────────────────────────────────
# Fetches upcoming Dublin AI and .NET events from Meetup RSS feeds and Eventbrite.
# Each function returns a list of event dicts compatible with build_event_card():
#   { title, url, month, day, tag, desc }
# Falls back to FALLBACK_* lists from sources.py if all live fetches fail/return nothing.

import re
import feedparser
from datetime import datetime
from html import unescape

from sources import (
    AI_EVENT_FEEDS, AI_EVENT_KEYWORDS,
    DOTNET_EVENT_FEEDS, DOTNET_EVENT_KEYWORDS,
)

SUMMARY_LEN = 200


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def _clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return unescape(text).strip()


def _parse_date(entry):
    """Try published_parsed then updated_parsed. Returns (month_str, day_str) or ('TBC', '—')."""
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = datetime(*val[:6])
                # Skip events that have already passed
                if dt < datetime.now():
                    return None, None
                return dt.strftime("%b"), str(dt.day)
            except Exception:
                pass
    return "TBC", "—"


def _to_event(entry, tag_label):
    """Convert a feedparser entry to an event dict."""
    title = _clean(entry.get("title", ""))
    url   = entry.get("link", "#")
    desc  = _clean(entry.get("summary", entry.get("description", "")))
    if len(desc) > SUMMARY_LEN:
        desc = desc[:SUMMARY_LEN - 1].rsplit(" ", 1)[0] + "…"
    if not desc:
        desc = "Dublin event. Click to see full details."
    month, day = _parse_date(entry)
    return {"title": title, "url": url, "month": month, "day": day, "tag": tag_label, "desc": desc}


def _fetch_events(feeds, keywords, tag_label, max_events):
    """
    Fetch events from a list of RSS feeds, filter by keywords, deduplicate,
    skip past events, and return up to max_events sorted by date.
    """
    results = []
    seen    = set()

    for source, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = _clean(entry.get("title", ""))
                if not title or title.lower() in seen:
                    continue

                # Keyword relevance check
                haystack = (title + " " + entry.get("summary", "")).lower()
                if not any(kw in haystack for kw in keywords):
                    continue

                event = _to_event(entry, tag_label)

                # Skip past events (parse_date returns None, None for those)
                if event["month"] is None:
                    continue

                seen.add(title.lower())
                results.append(event)

        except Exception as e:
            print(f"  ⚠  Could not fetch events from {feed_url}: {e}")

    # Sort: TBC goes to the end, dated events sorted by (month, day)
    def sort_key(ev):
        if ev["month"] == "TBC":
            return (99, 99)
        try:
            dt = datetime.strptime(f"{ev['month']} {ev['day']} 2026", "%b %d %Y")
            return (dt.month, dt.day)
        except Exception:
            return (98, 98)

    results.sort(key=sort_key)
    return results[:max_events]


# ─── PUBLIC API ────────────────────────────────────────────────────────────────

def fetch_dublin_ai_events(max_events=5):
    """Fetch upcoming Dublin AI / ML events dynamically."""
    events = _fetch_events(AI_EVENT_FEEDS, AI_EVENT_KEYWORDS, "AI · Dublin", max_events)
    print(f"  📅 Found {len(events)} live Dublin AI events")
    return events


def fetch_dublin_dotnet_events(max_events=4):
    """Fetch upcoming Dublin .NET / C# events dynamically."""
    events = _fetch_events(DOTNET_EVENT_FEEDS, DOTNET_EVENT_KEYWORDS, ".NET · Dublin", max_events)
    print(f"  📅 Found {len(events)} live Dublin .NET events")
    return events
