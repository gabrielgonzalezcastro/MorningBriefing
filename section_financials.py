# ─── FINANCIALS SECTION ────────────────────────────────────────────────────────
# Fetches current price and daily % change for a set of market indicators
# (crypto, indices, ETFs, commodities, UK investment trusts, FX) and renders
# a compact dashboard table in the morning briefing.

from html import escape
from datetime import date, timedelta

from sources import FINANCIAL_INDICATORS, TWITTER_ACCOUNTS

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("  Warning: yfinance not installed. Run: pip install yfinance")

try:
    from ntscraper import Nitter
    NT_AVAILABLE = True
except ImportError:
    NT_AVAILABLE = False
    print("  Warning: ntscraper not installed. Run: pip install ntscraper")

# ─── CURRENCY / FORMATTING RULES ────────────────────────────────────────────────

# Tickers that report in GBX (pence) — shown as raw pence with "p" suffix
_GBX_TICKERS = {"JGGI.L", "FCIT.L", "PCT.L", "JAM.L"}

# Tickers where we suppress the currency symbol (pure ratios / indices)
_NO_SYMBOL = {"^VIX", "EURUSD=X", "DX-Y.NYB"}

# Tickers that represent yields — value is already in % (e.g. 4.25 = 4.25%)
_YIELD_TICKERS = {"^TNX", "^TYX"}

_CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "GBX": "£"}


def _fmt_price(ticker, price, currency):
    if price is None:
        return "—"
    if ticker in _YIELD_TICKERS:
        return f"{price:.3f}%"                              # bond yield
    if ticker in _NO_SYMBOL:
        return f"{price:,.4f}" if ticker == "EURUSD=X" else f"{price:,.2f}"
    if ticker in _GBX_TICKERS:
        return f"{price:,.2f}p"                             # raw GBX pence
    sym = _CURRENCY_SYMBOLS.get((currency or "USD").upper(), "$")
    return f"{sym}{price:,.2f}"


def _fmt_chg(v):
    if v is None:
        return "—", ""
    sign   = "+" if v > 0 else ""
    cls    = "fin-pos" if v >= 0 else "fin-neg"
    return f"{sign}{v:.2f}%", cls


# ─── PRICE FETCHING ─────────────────────────────────────────────────────────────

def fetch_indicators():
    """
    Fetch current price and daily % change for every indicator in FINANCIAL_INDICATORS.
    Returns a list of dicts: { name, ticker, category, price_str, change_str, change_cls }
    """
    results = []

    if not YF_AVAILABLE:
        for name, ticker, category in FINANCIAL_INDICATORS:
            results.append({
                "name": name, "ticker": ticker, "category": category,
                "price_str": "—", "change_str": "—", "change_cls": "",
            })
        return results

    for name, ticker, category in FINANCIAL_INDICATORS:
        price_str  = "—"
        change_str = "—"
        change_cls = ""
        try:
            t    = yf.Ticker(ticker)
            info = t.fast_info

            price      = info.last_price
            prev_close = info.previous_close
            currency   = (getattr(info, "currency", "USD") or "USD").upper()

            if price is not None:
                price_str  = _fmt_price(ticker, float(price), currency)
                if prev_close:
                    chg = (price - prev_close) / prev_close * 100
                    change_str, change_cls = _fmt_chg(chg)

        except Exception as e:
            print(f"  Warning: could not fetch {ticker}: {e}")

        results.append({
            "name":       name,
            "ticker":     ticker,
            "category":   category,
            "price_str":  price_str,
            "change_str": change_str,
            "change_cls": change_cls,
        })

    return results


# ─── HTML BUILDER ────────────────────────────────────────────────────────────────

def _indicator_row(ind):
    name       = escape(ind["name"])
    ticker     = escape(ind["ticker"])
    category   = ind["category"]
    price_str  = ind["price_str"]
    change_str = ind["change_str"]
    change_cls = ind["change_cls"]

    return f"""\
  <div class="fin-row">
    <div class="fin-name-cell">
      <span class="fin-badge fin-badge-{category}">{category.upper()}</span>
      <div>
        <div class="fin-name">{name}</div>
        <div class="fin-ticker">{ticker}</div>
      </div>
    </div>
    <div class="fin-cell">{price_str}</div>
    <div class="fin-cell {change_cls}">{change_str}</div>
  </div>"""


def build_financials_section(build_section, build_subsection):
    """Fetch all indicators and render the Financials HTML section."""
    indicators = fetch_indicators()
    rows_html  = "\n".join(_indicator_row(ind) for ind in indicators)

    body = build_subsection("Market Indicators")
    body += f"""\
  <div class="fin-table">
    <div class="fin-header-row">
      <div class="fin-name-hdr">Indicator</div>
      <div class="fin-cell-hdr">Price</div>
      <div class="fin-cell-hdr">Day</div>
    </div>
{rows_html}
  </div>"""

    tweets_html = build_tweets_subsection(build_subsection)
    if tweets_html:
        body += "\n" + tweets_html

    return build_section(
        "financials", "&#x1F4CA;", "financials-title",
        "Financials", "sec-financials",
        body
    )


# ─── TWEETS ──────────────────────────────────────────────────────────────────

def fetch_latest_tweets(accounts=TWITTER_ACCOUNTS, max_per_account=3):
    """
    Fetch the latest tweets for each account in `accounts` using ntscraper.
    Returns a list of dicts: { handle, display_name, text, date, url }
    Only tweets from today or yesterday are included.
    """
    if not NT_AVAILABLE:
        return []

    results  = []
    cutoff   = date.today() - timedelta(days=1)

    try:
        scraper = Nitter(log_level=1, skip_instance_check=False)
    except Exception as e:
        print(f"  Warning: could not initialise Nitter scraper: {e}")
        return []

    for handle in accounts:
        try:
            data = scraper.get_tweets(handle, mode="user", number=max_per_account)
            for tweet in (data.get("tweets") or []):
                # ntscraper tweet keys: text, date, link, user (dict)
                raw_date = tweet.get("date", "")
                try:
                    # ntscraper returns dates like "Mar 22, 2026 · 9:14 AM UTC"
                    tweet_date = _parse_tweet_date(raw_date)
                except Exception:
                    tweet_date = None

                if tweet_date and tweet_date < cutoff:
                    continue  # skip old tweets

                user_info    = tweet.get("user") or {}
                display_name = escape(user_info.get("name") or handle)
                text         = escape(tweet.get("text") or "")
                link         = tweet.get("link") or f"https://x.com/{handle}"

                results.append({
                    "handle":       handle,
                    "display_name": display_name,
                    "text":         text,
                    "date":         raw_date,
                    "url":          link,
                })
        except Exception as e:
            print(f"  Warning: could not fetch tweets for @{handle}: {e}")

    return results


def _parse_tweet_date(raw: str) -> date:
    """Parse ntscraper date string like 'Mar 22, 2026 · 9:14 AM UTC' into a date."""
    # Strip the time part after ' · '
    raw = raw.split("·")[0].strip()
    from datetime import datetime
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw!r}")


def _tweet_card(tweet):
    handle       = escape(tweet["handle"])
    display_name = tweet["display_name"]
    text         = tweet["text"]
    url          = tweet["url"]
    date_str     = escape(tweet["date"])

    return f"""\
  <div class="tweet-card">
    <div class="tweet-header">
      <span class="tweet-name">{display_name}</span>
      <span class="tweet-handle">@{handle}</span>
      <span class="tweet-date">{date_str}</span>
    </div>
    <div class="tweet-body">{text}</div>
    <a class="tweet-link" href="{url}" target="_blank">View on X ↗</a>
  </div>"""


def build_tweets_subsection(build_subsection):
    """Fetch tweets and return the HTML subsection, or empty string if none."""
    tweets = fetch_latest_tweets()
    if not tweets:
        return "No Tweets"

    html  = build_subsection("Latest Tweets")
    html += "\n".join(_tweet_card(t) for t in tweets)
    return html
