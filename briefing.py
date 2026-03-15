import feedparser
import smtplib
import os
import re
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from html import escape

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SMTP_SERVER  = "smtp-relay.brevo.com"
SMTP_PORT    = 587
SMTP_LOGIN   = os.environ["BREVO_LOGIN"]
SMTP_KEY     = os.environ["BREVO_KEY"]
RECIPIENT    = "gabrielnoise@gmail.com"

MAX_AI       = 10
MAX_AI_DEV   = 5
MAX_DOTNET   = 10
MAX_APPIAN   = 10
SUMMARY_LEN  = 160   # max chars for concise summaries

# ─── RSS FEEDS ─────────────────────────────────────────────────────────────────

AI_FEEDS = [
    ("TechCrunch",         "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge",          "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat",        "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica",       "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Wired",              "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("MIT Tech Review",    "https://www.technologyreview.com/feed/"),
    ("The Register",       "https://www.theregister.com/headlines.atom"),
]

AI_DEV_FEEDS = [
    ("LogRocket",              "https://blog.logrocket.com/feed/"),
    ("The Pragmatic Engineer", "https://newsletter.pragmaticengineer.com/feed"),
    ("SD Times",               "https://sdtimes.com/feed/"),
    ("InfoQ",                  "https://www.infoq.com/ai/rss"),
    ("Dev.to AI",              "https://dev.to/feed/tag/ai"),
]

DOTNET_FEEDS = [
    ("MS .NET Blog",   "https://devblogs.microsoft.com/dotnet/feed/"),
    ("MS DevBlogs",    "https://devblogs.microsoft.com/feed/"),
    ("JetBrains .NET", "https://blog.jetbrains.com/dotnet/feed/"),
    ("Hanselman",      "https://feeds.hanselman.com/ScottHanselman"),
    (".NET Ketchup",   "https://dotnetketchup.com/feed"),
]

APPIAN_FEEDS = [
    ("Appian Blog",              "https://appian.com/blog/rss.xml"),
    ("Process Excellence",       "https://www.processexcellencenetwork.com/rss.xml"),
    ("AIthority",                "https://aithority.com/feed/"),
    ("Yahoo Finance",            "https://finance.yahoo.com/rss/2.0/headline?s=APPN&region=US&lang=en-US"),
    ("GuruFocus",                "https://www.gurufocus.com/news/rss?symbol=APPN"),
]

# ─── DUBLIN EVENTS (static — update as needed) ─────────────────────────────────

DUBLIN_AI_EVENTS = [
    {
        "title": "ICAIBR — International Conference on AI in Bioinformatics Research",
        "url":   "https://internationalconferencealerts.com/ireland/artificial-intelligence",
        "month": "Mar", "day": "31",
        "tag":   "AI · Conference",
        "desc":  "Dublin. Academic conference covering AI applications in bioinformatics research workflows.",
    },
    {
        "title": "ICAIBWA — International Conference on AI in Bioinformatics Workflow Automation",
        "url":   "https://internationalconferencealerts.com/ireland/artificial-intelligence",
        "month": "Apr", "day": "3",
        "tag":   "AI · Conference",
        "desc":  "Dublin. Focused on automating bioinformatics workflows using AI and ML techniques.",
    },
    {
        "title": "Dublin Tech Summit 2026",
        "url":   "https://dublintechsummit.tech/",
        "month": "May", "day": "27",
        "tag":   "Tech · AI · Dev",
        "desc":  "RDS Dublin, May 27–28. Covers AI, enterprise software, cybersecurity, fintech, and digital transformation.",
    },
    {
        "title": "IAPP AI Governance Global Europe 2026",
        "url":   "https://iapp.org/conference/iapp-ai-governance-global-europe/",
        "month": "Jun", "day": "1",
        "tag":   "AI · Governance",
        "desc":  "Dublin, Jun 1–4. The premier European event on AI policy, regulation, and the EU AI Act.",
    },
    {
        "title": "The Dublin AI Conference 2026",
        "url":   "https://dublin.ie/whats-on/listings/the-dublin-ai-conference/",
        "month": "TBC", "day": "—",
        "tag":   "AI · Networking",
        "desc":  "Gathers 400+ of Ireland's AI, business, and tech leaders for an evening of content and pre-arranged networking.",
    },
]

DUBLIN_DOTNET_EVENTS = [
    {
        "title": "Dublin Tech Summit 2026",
        "url":   "https://dublintechsummit.tech/",
        "month": "May", "day": "27",
        "tag":   "Tech · .NET · Dev",
        "desc":  "RDS Dublin, May 27–28. Software development, cloud, and enterprise tech across all stacks.",
    },
    {
        "title": ".NET Conf 2026 (Virtual — Watch from Dublin)",
        "url":   "https://www.dotnetconf.net/",
        "month": "Nov", "day": "TBC",
        "tag":   ".NET · Virtual",
        "desc":  "Microsoft's annual .NET conference. Free, virtual, and globally streamed — perfect for watching from home.",
    },
]

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
    Fetch RSS entries from the given feeds.
    If `keyword` is provided, only entries whose title or summary contain it are kept.
    """
    entries    = []
    seen_titles = set()

    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue

                summary = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                summary = re.sub(r"\s+", " ", summary)
                if len(summary) > SUMMARY_LEN:
                    summary = summary[:SUMMARY_LEN - 1].rsplit(" ", 1)[0] + "…"

                # keyword filter (case-insensitive)
                if keyword and keyword.lower() not in (title + " " + summary).lower():
                    continue

                seen_titles.add(title)

                # Parse publish date
                pub_date = ""
                for attr in ("published_parsed", "updated_parsed"):
                    val = getattr(entry, attr, None)
                    if val:
                        try:
                            pub_date = datetime(*val[:6]).strftime("%b %-d, %Y")
                            break
                        except Exception:
                            pass

                entries.append({
                    "title":    title,
                    "url":      entry.get("link", "#"),
                    "summary":  summary,
                    "source":   source,
                    "label":    detect_label(title + " " + summary),
                    "pub_date": pub_date,
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

    # ── AI section ───────────────────────────────────────────────────────────
    ai_body = build_subsection("Top Stories")
    ai_body += "\n".join(build_card(e, "highlight-ai" if i == 0 else "")
                         for i, e in enumerate(ai_entries))
    if ai_dev_entries:
        ai_body += "\n" + build_subsection("AI &amp; Software Development")
        ai_body += "\n".join(build_card(e) for e in ai_dev_entries)
    if DUBLIN_AI_EVENTS:
        ai_body += "\n" + build_subsection("Dublin Events")
        ai_body += "\n".join(build_event_card(e, i == 0)
                             for i, e in enumerate(DUBLIN_AI_EVENTS))

    # ── .NET section ─────────────────────────────────────────────────────────
    dotnet_body = "\n".join(build_card(e, "highlight-dotnet" if i == 0 else "")
                            for i, e in enumerate(dotnet_entries))
    if DUBLIN_DOTNET_EVENTS:
        dotnet_body += "\n" + build_subsection("Dublin Events")
        dotnet_body += "\n".join(build_event_card(e, i == 0)
                                 for i, e in enumerate(DUBLIN_DOTNET_EVENTS))

    # ── Appian section ───────────────────────────────────────────────────────
    appian_body = "\n".join(build_card(e, "highlight-appian" if i == 0 else "")
                            for i, e in enumerate(appian_entries))

    ai_section     = build_section("ai",     "&#x1F9E0;", "ai-title",     "Artificial Intelligence", "sec-ai",     ai_body)
    dotnet_section = build_section("dotnet", "&#x2699;&#xFE0F;", "dotnet-title", ".NET &amp; C#",         "sec-dotnet", dotnet_body)
    appian_section = build_section("appian", "&#x26A1;",  "appian-title", "Appian",                  "sec-appian", appian_body)

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
    --accent-ai:#a78bfa;--accent-ai-dim:rgba(167,139,250,0.12);
    --accent-dotnet:#60a5fa;--accent-dotnet-dim:rgba(96,165,250,0.12);
    --accent-appian:#06b6d4;--accent-appian-dim:rgba(6,182,212,0.12);
    --accent-event:#fb923c;--accent-event-dim:rgba(251,146,60,0.12);
    --accent-green:#34d399;
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
  .section-icon.ai{{background:var(--accent-ai-dim)}}
  .section-icon.dotnet{{background:var(--accent-dotnet-dim)}}
  .section-icon.appian{{background:var(--accent-appian-dim)}}
  .section-header h2{{font-family:'Playfair Display',serif;font-size:26px;font-weight:700;letter-spacing:-0.5px;flex:1}}
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
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
  @media(max-width:600px){{
    .container{{padding:24px 16px 60px}}
    .card{{padding:16px 18px}}
    .card-top{{flex-direction:column;gap:6px}}
    .event-card{{flex-direction:column;gap:12px}}
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
    today = datetime.now().strftime("%A, %B %-d, %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☕ Morning Briefing — {today}"
    msg["From"]    = "Gabo's Briefing <gabrielnoise@gmail.com>"
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_KEY)
        server.sendmail(SMTP_LOGIN, RECIPIENT, msg.as_string())
    print(f"✅ Email sent to {RECIPIENT}")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📡 Fetching AI news...")
    ai_entries = fetch_entries(AI_FEEDS, MAX_AI)
    print(f"   Got {len(ai_entries)} articles")

    print("📡 Fetching AI dev news...")
    ai_dev_entries = fetch_entries(AI_DEV_FEEDS, MAX_AI_DEV)
    print(f"   Got {len(ai_dev_entries)} articles")

    print("📡 Fetching .NET news...")
    dotnet_entries = fetch_entries(DOTNET_FEEDS, MAX_DOTNET)
    print(f"   Got {len(dotnet_entries)} articles")

    print("📡 Fetching Appian news...")
    appian_entries = fetch_entries(APPIAN_FEEDS, MAX_APPIAN, keyword="appian")
    print(f"   Got {len(appian_entries)} articles")

    print("🔨 Building HTML...")
    html_content = build_html(ai_entries, ai_dev_entries, dotnet_entries, appian_entries)

    print("📧 Sending email...")
    send_email(html_content)
