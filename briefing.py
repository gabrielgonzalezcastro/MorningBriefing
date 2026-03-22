import feedparser
import smtplib
import os
import re
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from html import escape

from section_portfolio import build_portfolio_section
from section_ai        import fetch_ai_entries,     build_ai_section
from section_dotnet    import fetch_dotnet_entries, build_dotnet_section
from section_appian    import fetch_appian_entries, build_appian_section

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SMTP_SERVER  = "smtp-relay.brevo.com"
SMTP_PORT    = 587
SMTP_LOGIN   = os.environ["BREVO_LOGIN"]
SMTP_KEY     = os.environ["BREVO_KEY"]
RECIPIENT    = "gabrielnoise@gmail.com"

SUMMARY_LEN  = 160   # max chars for concise summaries

# ─── LABEL DETECTION ───────────────────────────────────────────────────────────

LABEL_RULES = [
    ("breaking",   r"\bbreaking\b|\burgent\b|\bexclusive\b"),
    ("security",   r"\bsecurity\b|\bvulnerabilit\b|\bCVE\b|\bpatch\b|\bzero.?day\b|\bexploit\b"),
    ("funding",    r"\bfunding\b|\braised?\b|\bbillion\b|\bmillion\b|\binvestment\b|\bvaluation\b"),
    ("models",     r"\bmodel\b|\bGPT\b|\bClaude\b|\bGemini\b|\bLLM\b|\bparameter\b"),
    ("research",   r"\bresearch\b|\bpaper\b|\bstudy\b|\bscientist\b|\buniversit\b|\bNature\b"),
    ("hardware",   r"\bchip\b|\bGPU\b|\bhardware\b|\bNvidia\b|\bprocessor\b|\bdevice\b"),
    ("agents",     r"\bagent\b|\bagentic\b|\bautonomous\b|\borchestrat\b"),
    ("enterprise", r"\benterprise\b|\bbusiness\b|\bcompan\b|\bstartup\b|\bproductivit\b"),
    ("release",    r"\bannouncing\b|\blaunching\b|\bnew\b|\bships?\b|\bavailable\b"),
    ("tools",      r"\bvisual studio\b|\bVS Code\b|\bIDE\b|\btooling\b|\bextension\b|\bplugin\b|\bcursor\b|\bwindsurf\b|\bcopilot\b"),
    ("finance",    r"\bearnings\b|\brevenue\b|\bstock\b|\bNASDAQ\b|\bEPS\b|\bguidance\b|\bshares?\b"),
    ("security",   r"\bpatch\b|\bfix\b|\bCVE\b|\bvulnerabilit\b"),
    ("update",     r"\bupdate\b|\bservicing\b|\bimprove\b|\benhance\b"),
]

LABEL_STYLES = {
    "breaking":   ("rgba(239,68,68,0.15)",   "#f87171"),
    "funding":    ("rgba(251,191,36,0.15)",  "#fbbf24"),
    "models":     ("rgba(167,139,250,0.15)", "#a78bfa"),
    "agents":     ("rgba(167,139,250,0.15)", "#a78bfa"),
    "enterprise": ("rgba(52,211,153,0.15)",  "#34d399"),
    "hardware":   ("rgba(96,165,250,0.15)",  "#60a5fa"),
    "research":   ("rgba(244,114,182,0.15)", "#f472b6"),
    "security":   ("rgba(239,68,68,0.15)",   "#f87171"),
    "release":    ("rgba(96,165,250,0.15)",  "#60a5fa"),
    "update":     ("rgba(52,211,153,0.15)",  "#34d399"),
    "tools":      ("rgba(251,191,36,0.15)",  "#fbbf24"),
    "finance":    ("rgba(251,191,36,0.15)",  "#fbbf24"),
}

def detect_label(text):
    for label, pattern in LABEL_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return "update"

def label_style(label):
    bg, color = LABEL_STYLES.get(label, ("rgba(100,100,130,0.15)", "#aaaacc"))
    return f'background:{bg};color:{color}'

# ─── FEED FETCHING ─────────────────────────────────────────────────────────────

def fetch_entries(feeds, max_items, keyword=None):
    """
    Fetch RSS entries published yesterday.
    Scans up to 50 entries per feed to find yesterday's articles.
    If `keyword` is provided, only entries whose title or summary contain it are kept.
    """
    entries     = []
    seen_titles = set()
    yesterday   = date.today() - timedelta(days=1)

    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:50]:   # scan wider to find yesterday's articles
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue

                # ── Date check first — skip anything not from yesterday ──────────
                pub_date_obj = None
                pub_date_str = ""
                for attr in ("published_parsed", "updated_parsed"):
                    val = getattr(entry, attr, None)
                    if val:
                        try:
                            pub_date_obj = date(*val[:3])
                            pub_date_str = datetime(*val[:6]).strftime("%b %-d, %Y")
                            break
                        except Exception:
                            pass

                if pub_date_obj != yesterday:
                    continue   # skip articles with no date or not from yesterday

                # ── Summary ──────────────────────────────────────────────────────
                summary = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                summary = re.sub(r"\s+", " ", summary)
                if len(summary) > SUMMARY_LEN:
                    summary = summary[:SUMMARY_LEN - 1].rsplit(" ", 1)[0] + "…"

                # ── Keyword filter (pipe-separated OR terms) ──────────────────────
                if keyword:
                    haystack = (title + " " + summary).lower()
                    terms = [t.strip() for t in keyword.split("|")]
                    if not any(t in haystack for t in terms):
                        continue

                seen_titles.add(title)
                entries.append({
                    "title":    title,
                    "url":      entry.get("link", "#"),
                    "summary":  summary,
                    "source":   source,
                    "label":    detect_label(title + " " + summary),
                    "pub_date": pub_date_str,
                })

                if len(entries) >= max_items:
                    return entries

        except Exception as e:
            print(f"  Warning: could not fetch {url}: {e}")

    return entries[:max_items]

# ─── HTML COMPONENTS ───────────────────────────────────────────────────────────

CHEVRON = '<div class="chevron"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></div>'

def build_card(entry, highlight_class=""):
    label     = entry["label"]
    title     = escape(entry["title"])
    summary   = escape(entry["summary"])
    url       = entry["url"]
    source    = escape(entry["source"])
    pub_date  = escape(entry.get("pub_date", ""))
    l_style   = label_style(label)
    h_class   = f' {highlight_class}' if highlight_class else ''
    date_html = f'<span class="pub-date">{pub_date}</span>' if pub_date else ''
    return f"""  <div class="card{h_class}">
    <div class="card-top">
      <div class="card-title-wrap">
        <h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
        {date_html}
      </div>
      <span class="card-label" style="{l_style}">{label.upper()}</span>
    </div>
    <p>{summary}</p>
    <div class="source"><a href="{url}" target="_blank" rel="noopener">{source}</a></div>
  </div>"""

def build_subsection(title):
    return f'  <div class="subsection-title">{escape(title)}</div>\n'

def build_event_card(event, highlight=False):
    title  = escape(event["title"])
    url    = event["url"]
    month  = escape(event["month"])
    day    = escape(str(event["day"]))
    tag    = escape(event["tag"])
    desc   = escape(event["desc"])
    h_cls  = ' highlight-event' if highlight else ''
    day_fs = 'font-size:16px;' if len(day) > 2 else ''
    return f"""  <div class="event-card{h_cls}">
    <div class="event-date-block">
      <div class="month">{month}</div>
      <div class="day" style="{day_fs}">{day}</div>
    </div>
    <div class="event-body">
      <div class="event-tag">{tag}</div>
      <h4><a href="{url}" target="_blank" rel="noopener">{title}</a></h4>
      <p>{desc}</p>
    </div>
  </div>"""

def build_section(icon_cls, icon_char, h2_cls, title, section_id, body_html):
    return f"""  <div class="section-header" onclick="toggleSection(this)" id="{section_id}">
    <div class="section-icon {icon_cls}">{icon_char}</div>
    <h2 class="{h2_cls}">{title}</h2>
    {CHEVRON}
  </div>
  <div class="section-body">
{body_html}
  </div>"""

# ─── HTML BUILDER ──────────────────────────────────────────────────────────────

def build_html(ai_entries, ai_dev_entries, dotnet_entries, appian_entries):
    today = datetime.now().strftime("%A, %B %-d, %Y")

    portfolio_section = build_portfolio_section(build_section)
    ai_section        = build_ai_section(
        ai_entries, ai_dev_entries,
        build_card, build_subsection, build_event_card, build_section
    )
    dotnet_section    = build_dotnet_section(
        dotnet_entries,
        build_card, build_subsection, build_event_card, build_section
    )
    appian_section    = build_appian_section(
        appian_entries,
        build_card, build_section
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Briefing &mdash; {today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0f0f13;--surface:#18181f;--border:#2a2a38;--text:#e8e8ed;
    --text-muted:#8888a0;
    --accent-portfolio:#f59e0b;--accent-portfolio-dim:rgba(245,158,11,0.12);
    --accent-ai:#a78bfa;--accent-ai-dim:rgba(167,139,250,0.12);
    --accent-dotnet:#60a5fa;--accent-dotnet-dim:rgba(96,165,250,0.12);
    --accent-appian:#06b6d4;--accent-appian-dim:rgba(6,182,212,0.12);
    --accent-event:#fb923c;--accent-event-dim:rgba(251,146,60,0.12);
    --accent-green:#34d399;--accent-red:#f87171;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}}
  .container{{max-width:900px;margin:0 auto;padding:40px 24px 80px}}
  /* Header */
  .header{{text-align:center;margin-bottom:56px;padding-bottom:40px;border-bottom:1px solid var(--border)}}
  .header-label{{display:inline-block;font-size:11px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:var(--text-muted);margin-bottom:16px;background:var(--surface);padding:6px 16px;border-radius:20px;border:1px solid var(--border)}}
  .header h1{{font-family:'Playfair Display',serif;font-size:clamp(36px,6vw,56px);font-weight:800;letter-spacing:-1px;margin-bottom:12px;background:linear-gradient(135deg,#e8e8ed 0%,#a0a0b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .header-date{{font-size:15px;color:var(--text-muted)}}
  .header-date span{{color:var(--accent-green);font-weight:500}}
  /* Section */
  .section-header{{display:flex;align-items:center;gap:14px;margin-bottom:20px;margin-top:52px;cursor:pointer;user-select:none}}
  .section-header:hover .chevron{{opacity:1}}
  .section-icon{{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}}
  .section-icon.portfolio{{background:var(--accent-portfolio-dim)}}
  .section-icon.ai{{background:var(--accent-ai-dim)}}
  .section-icon.dotnet{{background:var(--accent-dotnet-dim)}}
  .section-icon.appian{{background:var(--accent-appian-dim)}}
  .section-header h2{{font-family:'Playfair Display',serif;font-size:26px;font-weight:700;letter-spacing:-0.5px;flex:1}}
  .section-header h2.portfolio-title{{color:var(--accent-portfolio)}}
  .section-header h2.ai-title{{color:var(--accent-ai)}}
  .section-header h2.dotnet-title{{color:var(--accent-dotnet)}}
  .section-header h2.appian-title{{color:var(--accent-appian)}}
  .chevron{{width:28px;height:28px;border-radius:8px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;flex-shrink:0;opacity:0.6;transition:opacity 0.2s}}
  .chevron svg{{transition:transform 0.3s ease}}
  .section-header.collapsed .chevron svg{{transform:rotate(-90deg)}}
  .section-body{{overflow:hidden;transition:max-height 0.4s ease,opacity 0.3s ease;max-height:9999px;opacity:1}}
  .section-body.collapsed{{max-height:0;opacity:0}}
  /* Subsection */
  .subsection-title{{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--text-muted);margin:28px 0 14px;padding-left:10px;border-left:2px solid var(--border)}}
  /* Cards */
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px 24px;margin-bottom:10px;transition:border-color 0.2s,transform 0.2s;animation:fadeUp 0.4s ease both}}
  .card:hover{{border-color:#3a3a4f;transform:translateY(-1px)}}
  .card-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:8px}}
  .card-title-wrap{{flex:1;min-width:0}}
  .pub-date{{display:block;font-size:11px;color:#505068;margin-top:5px;letter-spacing:0.2px}}
  .card-label{{display:inline-block;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:3px 8px;border-radius:5px;white-space:nowrap;flex-shrink:0;margin-top:3px}}
  .card h3{{font-size:15px;font-weight:700;line-height:1.4}}
  .card h3 a{{color:inherit;text-decoration:none;transition:opacity 0.15s}}
  .card h3 a:hover{{opacity:0.7;text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}}
  .card p{{font-size:13px;color:var(--text-muted);line-height:1.65}}
  .card .source{{margin-top:10px;font-size:11px;display:flex;align-items:center;gap:5px}}
  .card .source a{{color:#606080;text-decoration:none}}
  .card .source a:hover{{color:#9090b8;text-decoration:underline}}
  .card.highlight-ai{{border-color:rgba(167,139,250,0.3);background:linear-gradient(135deg,rgba(167,139,250,0.07) 0%,var(--surface) 100%)}}
  .card.highlight-dotnet{{border-color:rgba(96,165,250,0.3);background:linear-gradient(135deg,rgba(96,165,250,0.07) 0%,var(--surface) 100%)}}
  .card.highlight-appian{{border-color:rgba(6,182,212,0.3);background:linear-gradient(135deg,rgba(6,182,212,0.07) 0%,var(--surface) 100%)}}
  /* Event cards */
  .event-card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 22px;margin-bottom:10px;display:flex;gap:18px;align-items:flex-start;transition:border-color 0.2s,transform 0.2s;animation:fadeUp 0.4s ease both}}
  .event-card:hover{{border-color:rgba(251,146,60,0.3);transform:translateY(-1px)}}
  .event-card.highlight-event{{border-color:rgba(251,146,60,0.3);background:linear-gradient(135deg,rgba(251,146,60,0.07) 0%,var(--surface) 100%)}}
  .event-date-block{{flex-shrink:0;background:var(--accent-event-dim);border:1px solid rgba(251,146,60,0.2);border-radius:10px;padding:8px 12px;text-align:center;min-width:56px}}
  .event-date-block .month{{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent-event)}}
  .event-date-block .day{{font-size:22px;font-weight:800;color:var(--text);line-height:1.1}}
  .event-body h4{{font-size:14px;font-weight:700;margin-bottom:4px}}
  .event-body h4 a{{color:inherit;text-decoration:none}}
  .event-body h4 a:hover{{opacity:0.7;text-decoration:underline}}
  .event-body p{{font-size:12px;color:var(--text-muted);line-height:1.55}}
  .event-tag{{display:inline-block;font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:2px 7px;border-radius:4px;background:rgba(251,146,60,0.12);color:var(--accent-event);margin-bottom:6px}}
  /* Misc */
  .divider{{height:1px;background:var(--border);margin:48px 0}}
  .footer{{text-align:center;padding-top:32px;border-top:1px solid var(--border);margin-top:56px}}
  .footer p{{font-size:12px;color:#444460}}
  /* Portfolio table */
  .pf-table{{border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-top:8px}}
  .pf-header-row,.pf-row,.pf-total-row{{display:grid;grid-template-columns:2.2fr 1fr 0.9fr 1.1fr 1.1fr 0.9fr;align-items:center}}
  .pf-header-row{{background:rgba(255,255,255,0.03);border-bottom:1px solid var(--border);padding:10px 18px}}
  .pf-cell-hdr{{font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted);text-align:right}}
  .pf-asset-hdr{{font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted)}}
  .pf-row{{padding:14px 18px;border-bottom:1px solid rgba(42,42,56,0.7);transition:background 0.15s}}
  .pf-row:last-of-type{{border-bottom:none}}
  .pf-row:hover{{background:rgba(255,255,255,0.02)}}
  .pf-total-row{{padding:12px 18px;background:rgba(245,158,11,0.07);border-top:1px solid var(--border)}}
  .pf-asset-cell{{display:flex;align-items:center;gap:10px}}
  .pf-name{{font-size:14px;font-weight:600;color:var(--text)}}
  .pf-ticker{{font-size:11px;color:var(--text-muted);margin-top:2px}}
  .pf-cell{{font-size:13px;font-weight:500;text-align:right;color:var(--text)}}
  .pf-badge{{display:inline-block;font-size:8px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:3px 7px;border-radius:4px;white-space:nowrap}}
  .pf-badge-stock{{background:rgba(96,165,250,0.15);color:#60a5fa}}
  .pf-badge-etf{{background:rgba(52,211,153,0.15);color:#34d399}}
  .pf-badge-crypto{{background:rgba(167,139,250,0.15);color:#a78bfa}}
  .pf-pos{{color:var(--accent-green)!important}}
  .pf-neg{{color:var(--accent-red)!important}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
  @media(max-width:600px){{
    .container{{padding:24px 16px 60px}}
    .card{{padding:16px 18px}}
    .card-top{{flex-direction:column;gap:6px}}
    .event-card{{flex-direction:column;gap:12px}}
    .pf-header-row,.pf-row,.pf-total-row{{grid-template-columns:1.8fr 0.9fr 0.8fr 1fr 1fr 0.8fr;font-size:11px}}
    .pf-header-row,.pf-row,.pf-total-row{{padding:10px 12px}}
  }}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div class="header-label">Daily Briefing</div>
    <h1>Morning Briefing</h1>
    <p class="header-date">{today} &mdash; Dublin, Ireland &bull; <span>Live</span></p>
  </header>

{portfolio_section}

  <div class="divider"></div>

{ai_section}

  <div class="divider"></div>

{dotnet_section}

  <div class="divider"></div>

{appian_section}

  <footer class="footer">
    <p>Gabo's Morning Briefing &bull; Auto-generated on {today} &bull; Powered by Claude</p>
  </footer>
</div>
<script>
  function toggleSection(header) {{
    const body = header.nextElementSibling;
    const collapsed = body.classList.contains('collapsed');
    header.classList.toggle('collapsed', !collapsed);
    body.classList.toggle('collapsed', !collapsed);
  }}
</script>
</body>
</html>"""

# ─── EMAIL SENDER ──────────────────────────────────────────────────────────────

def send_email(html_content):
    today      = datetime.now().strftime("%A, %B %-d, %Y")
    today_file = datetime.now().strftime("%Y-%m-%d")

    # Outer wrapper — "mixed" allows both a rendered body and file attachments
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"☕ Morning Briefing — {today}"
    msg["From"]    = "Gabo's Briefing <gabrielnoise@gmail.com>"
    msg["To"]      = RECIPIENT

    # ── Inline HTML body ─────────────────────────────────────────────────────
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(html_content, "html"))
    msg.attach(body)

    # ── HTML file attachment ─────────────────────────────────────────────────
    attachment = MIMEText(html_content, "html")
    attachment.add_header(
        "Content-Disposition", "attachment",
        filename=f"morning-briefing-{today_file}.html"
    )
    msg.attach(attachment)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_KEY)
        server.sendmail(SMTP_LOGIN, RECIPIENT, msg.as_string())
    print(f"✅ Email sent to {RECIPIENT} (with HTML attachment)")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("💼 Loading portfolio...")

    print("📡 Fetching AI news...")
    ai_entries, ai_dev_entries = fetch_ai_entries(fetch_entries)
    print(f"   Got {len(ai_entries)} articles (top) + {len(ai_dev_entries)} (dev)")

    print("📡 Fetching .NET news...")
    dotnet_entries = fetch_dotnet_entries(fetch_entries)
    print(f"   Got {len(dotnet_entries)} articles")

    print("📡 Fetching Appian news...")
    appian_entries = fetch_appian_entries(fetch_entries)
    print(f"   Got {len(appian_entries)} articles")

    print("🔨 Building HTML...")
    html_content = build_html(ai_entries, ai_dev_entries, dotnet_entries, appian_entries)

    print("📧 Sending email...")
    send_email(html_content)
