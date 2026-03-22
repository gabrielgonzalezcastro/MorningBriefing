# ─── .NET & C# SECTION ─────────────────────────────────────────────────────────
# Everything related to the .NET & C# section:
# constants, feed fetching, and HTML building.

from sources import DOTNET_FEEDS
from events import fetch_dublin_dotnet_events

MAX_DOTNET = 10


def fetch_dotnet_entries(fetch_entries_fn):
    """Fetch .NET & C# articles. Returns a list of entries."""
    return fetch_entries_fn(DOTNET_FEEDS, MAX_DOTNET)


def build_dotnet_section(dotnet_entries,
                         build_card, build_subsection, build_event_card, build_section):
    """Build and return the full HTML for the .NET & C# section."""
    body = "\n".join(
        build_card(e, "highlight-dotnet" if i == 0 else "")
        for i, e in enumerate(dotnet_entries)
    )

    dublin_dotnet_events = fetch_dublin_dotnet_events()
    if dublin_dotnet_events:
        body += "\n" + build_subsection("Dublin Events")
        body += "\n".join(
            build_event_card(e, i == 0)
            for i, e in enumerate(dublin_dotnet_events)
        )

    return build_section(
        "dotnet", "&#x2699;&#xFE0F;", "dotnet-title",
        ".NET &amp; C#", "sec-dotnet",
        body
    )
