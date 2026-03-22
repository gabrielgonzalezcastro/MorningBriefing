# ─── APPIAN SECTION ────────────────────────────────────────────────────────────
# Everything related to the Appian section:
# constants, keyword filter, feed fetching, and HTML building.

from sources import APPIAN_FEEDS

MAX_APPIAN = 10

# Only entries matching at least one of these terms are kept.
APPIAN_KEYWORD = "appian|low-code|lowcode|no-code|bpm|process automation"


def fetch_appian_entries(fetch_entries_fn):
    """Fetch Appian / low-code / BPM articles. Returns a list of entries."""
    return fetch_entries_fn(APPIAN_FEEDS, MAX_APPIAN, keyword=APPIAN_KEYWORD)


def build_appian_section(appian_entries,
                         build_card, build_section):
    """Build and return the full HTML for the Appian section."""
    body = "\n".join(
        build_card(e, "highlight-appian" if i == 0 else "")
        for i, e in enumerate(appian_entries)
    )

    return build_section(
        "appian", "&#x26A1;", "appian-title",
        "Appian", "sec-appian",
        body
    )
