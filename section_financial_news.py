# ─── FINANCIAL NEWS SECTION ────────────────────────────────────────────────────
# Fetches yesterday's articles from FINANCIAL_NEWS_FEEDS and renders them
# as a news card list in the morning briefing.

from sources import FINANCIAL_NEWS_FEEDS

MAX_FINANCIAL_NEWS = 15


def fetch_financial_news_entries(fetch_entries_fn):
    """Fetch financial news articles from yesterday. Returns a list of entries."""
    return fetch_entries_fn(FINANCIAL_NEWS_FEEDS, MAX_FINANCIAL_NEWS)


def build_financial_news_section(financial_news_entries,
                                 build_card, build_section):
    """Build and return the full HTML for the Financial News section."""
    if not financial_news_entries:
        body = '  <p style="color:var(--text-muted);font-size:13px;padding:8px 0">No articles found for yesterday.</p>'
    else:
        body = "\n".join(
            build_card(e, "highlight-financial-news" if i == 0 else "")
            for i, e in enumerate(financial_news_entries)
        )

    return build_section(
        "financial-news", "&#x1F4B9;", "financial-news-title",
        "Financial News", "sec-financial-news",
        body
    )
