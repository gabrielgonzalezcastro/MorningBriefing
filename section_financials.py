# ─── FINANCIALS SECTION ────────────────────────────────────────────────────────
# Fetches current price and daily % change for a set of market indicators
# (crypto, indices, ETFs, commodities, UK investment trusts, FX) and renders
# a compact dashboard table in the morning briefing.

from html import escape

from sources import FINANCIAL_INDICATORS

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("  Warning: yfinance not installed. Run: pip install yfinance")

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


def build_financials_section(build_section):
    """Fetch all indicators and render the Financials HTML section."""
    indicators = fetch_indicators()
    rows_html  = "\n".join(_indicator_row(ind) for ind in indicators)

    body = f"""\
  <div class="fin-table">
    <div class="fin-header-row">
      <div class="fin-name-hdr">Indicator</div>
      <div class="fin-cell-hdr">Price</div>
      <div class="fin-cell-hdr">Day</div>
    </div>
{rows_html}
  </div>"""

    return build_section(
        "financials", "&#x1F4CA;", "financials-title",
        "Financials", "sec-financials",
        body
    )
