# ─── PORTFOLIO PERFORMANCE SECTION ─────────────────────────────────────────────
# Loads holdings from portfolio.json, fetches live prices via Yahoo Finance,
# converts everything to EUR, computes P&L, and builds the HTML section.
#
# portfolio.json fields per asset:
#   name                — display name
#   ticker              — Yahoo Finance ticker (NKE, AAPL, BTC-EUR, VWCE.DE, …)
#   type                — "stock" | "etf" | "crypto"
#   units               — number of shares / coins held
#   amount_invested_eur — your total cost basis in EUR

import json
import os
from html import escape

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("  Warning: yfinance not installed. Run: pip install yfinance")

# ─── LOAD PORTFOLIO ─────────────────────────────────────────────────────────────

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")


def load_portfolio():
    """Load and return the list of assets from portfolio.json."""
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["assets"]


# ─── PRICE FETCHING ─────────────────────────────────────────────────────────────

def _get_eur_usd_rate():
    """Fetch the current EUR/USD FX rate. Returns None on failure."""
    try:
        fx   = yf.Ticker("EURUSD=X")
        rate = fx.fast_info.last_price   # 1 EUR = rate USD
        return float(rate) if rate else None
    except Exception as e:
        print(f"  Warning: could not fetch EUR/USD rate: {e}")
        return None


def fetch_prices(assets):
    """
    Fetch current price and daily % change for every asset via Yahoo Finance.
    Stores the native price (USD, EUR, etc.) for display, and converts to EUR
    for all value/P&L calculations.

    Returns a dict keyed by ticker:
        { price_native, currency, price_eur, change_pct }
    """
    if not YF_AVAILABLE:
        return {a["ticker"]: {"price_native": None, "currency": None,
                               "price_eur": None, "change_pct": None} for a in assets}

    eur_usd = _get_eur_usd_rate()   # 1 EUR = X USD  →  price_eur = price_usd / eur_usd
    prices  = {}

    for asset in assets:
        ticker = asset["ticker"]
        try:
            t    = yf.Ticker(ticker)
            info = t.fast_info

            price      = info.last_price
            prev_close = info.previous_close

            if price is None:
                raise ValueError("No price returned")

            change_pct   = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
            currency     = (getattr(info, "currency", "USD") or "USD").upper()
            price_native = float(price)   # raw price in asset's native currency

            if currency == "EUR":
                price_eur = price_native
            elif eur_usd:
                price_eur = price_native / eur_usd
            else:
                price_eur = None   # can't convert without FX rate

            prices[ticker] = {
                "price_native": price_native,
                "currency":     currency,
                "price_eur":    price_eur,
                "change_pct":   float(change_pct),
            }

        except Exception as e:
            print(f"  Warning: could not fetch price for {ticker}: {e}")
            prices[ticker] = {"price_native": None, "currency": None,
                               "price_eur": None, "change_pct": None}

    return prices


# ─── P&L CALCULATION ────────────────────────────────────────────────────────────

def compute_pnl(asset, price_data):
    """
    Enrich an asset dict with live price and computed P&L figures.

    Added keys:
        price_eur      — current price per unit in EUR
        change_pct     — daily % change
        current_value  — units × price_eur
        pnl_eur        — current_value − amount_invested_eur
        pnl_pct        — pnl_eur / amount_invested_eur × 100
    """
    price_native = price_data.get("price_native")
    currency     = price_data.get("currency")
    price_eur    = price_data.get("price_eur")
    change_pct   = price_data.get("change_pct")
    units        = float(asset.get("units", 0) or 0)
    invested     = float(asset.get("amount_invested_eur", 0) or 0)

    if price_eur is not None and units > 0:
        current_value = price_eur * units
        pnl_eur       = current_value - invested
        pnl_pct       = (pnl_eur / invested * 100) if invested else 0.0
    else:
        current_value = None
        pnl_eur       = None
        pnl_pct       = None

    avg_buying_price = asset.get("avg_buying_price")

    return {
        **asset,
        "price_native":    price_native,
        "currency":        currency,
        "price_eur":       price_eur,
        "change_pct":      change_pct,
        "current_value":   current_value,
        "pnl_eur":         pnl_eur,
        "pnl_pct":         pnl_pct,
        "avg_buying_price": avg_buying_price,
    }


# ─── FORMATTING HELPERS ──────────────────────────────────────────────────────────

def _native(v, currency):
    """Format the raw asset price with its native currency symbol."""
    if v is None:
        return "—"
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "GBX": "p"}
    sym = symbols.get(currency or "USD", f"{currency} " if currency else "$")
    return f"{sym}{v:,.2f}"

def _eur(v, sign=False):
    if v is None:
        return "—"
    prefix = "+" if (sign and v > 0) else ""
    return f"{prefix}€{v:,.2f}"

def _pct(v, sign=True):
    if v is None:
        return "—"
    prefix = "+" if (sign and v > 0) else ""
    return f"{prefix}{v:.2f}%"

def _cls(v):
    """Return CSS class name for positive/negative colouring."""
    if v is None:
        return ""
    return "pf-pos" if v >= 0 else "pf-neg"


# ─── HTML BUILDERS ───────────────────────────────────────────────────────────────

def _asset_row(row):
    name      = escape(row["name"])
    ticker    = escape(row["ticker"])
    atype     = escape(row.get("type", "stock").lower())
    badge_lbl = atype.upper()

    price_s  = _native(row["price_native"],    row.get("currency"))
    avg_s    = _native(row["avg_buying_price"], row.get("currency"))
    chg_s    = _pct(row["change_pct"])
    value_s  = _eur(row["current_value"])
    pnl_e_s  = _eur(row["pnl_eur"],  sign=True)
    pnl_p_s  = _pct(row["pnl_pct"])

    chg_cls = _cls(row["change_pct"])
    pnl_cls = _cls(row["pnl_eur"])

    return f"""\
  <div class="pf-row">
    <div class="pf-asset-cell">
      <span class="pf-badge pf-badge-{atype}">{badge_lbl}</span>
      <div>
        <div class="pf-name">{name}</div>
        <div class="pf-ticker">{ticker}</div>
      </div>
    </div>
    <div class="pf-cell">{price_s}</div>
    <div class="pf-cell {chg_cls}">{chg_s}</div>
    <div class="pf-cell">{value_s}</div>
    <div class="pf-cell">{avg_s}</div>
    <div class="pf-cell {pnl_cls}">{pnl_e_s}</div>
    <div class="pf-cell {pnl_cls}">{pnl_p_s}</div>
  </div>"""


def build_portfolio_section(build_section):
    """
    Load portfolio.json → fetch live prices → compute P&L → render HTML section.
    """
    assets = load_portfolio()
    prices = fetch_prices(assets)
    rows   = [compute_pnl(a, prices.get(a["ticker"], {})) for a in assets]

    # ── Portfolio totals ─────────────────────────────────────────────────────
    total_invested = sum(
        float(r.get("amount_invested_eur") or 0) for r in rows
    )
    total_value = sum(
        r["current_value"] for r in rows if r["current_value"] is not None
    )
    total_pnl_eur = (total_value - total_invested) if total_value else None
    total_pnl_pct = (
        (total_pnl_eur / total_invested * 100)
        if (total_pnl_eur is not None and total_invested)
        else None
    )
    total_cls = _cls(total_pnl_eur)

    rows_html = "\n".join(_asset_row(r) for r in rows)

    body = f"""\
  <div class="pf-table">
    <div class="pf-header-row">
      <div class="pf-asset-hdr">Asset</div>
      <div class="pf-cell-hdr">Price (native)</div>
      <div class="pf-cell-hdr">Day</div>
      <div class="pf-cell-hdr">Value (EUR)</div>
      <div class="pf-cell-hdr">Avg. Buy Price</div>
      <div class="pf-cell-hdr">P&amp;L (EUR)</div>
      <div class="pf-cell-hdr">P&amp;L %</div>
    </div>
{rows_html}
    <div class="pf-total-row">
      <div class="pf-asset-hdr">Total Portfolio</div>
      <div class="pf-cell-hdr"></div>
      <div class="pf-cell-hdr"></div>
      <div class="pf-cell-hdr">{_eur(total_value)}</div>
      <div class="pf-cell-hdr"></div>
      <div class="pf-cell-hdr {total_cls}">{_eur(total_pnl_eur, sign=True)}</div>
      <div class="pf-cell-hdr {total_cls}">{_pct(total_pnl_pct)}</div>
    </div>
  </div>"""

    return build_section(
        "portfolio", "&#x1F4C8;", "portfolio-title",
        "Portfolio Performance", "sec-portfolio",
        body
    )
