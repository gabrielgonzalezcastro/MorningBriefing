import feedparser
import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from html import escape

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT   = 587
SMTP_LOGIN  = os.environ["BREVO_LOGIN"]
SMTP_KEY    = os.environ["BREVO_KEY"]
RECIPIENT   = "gabrielnoise@gmail.com"
MAX_AI      = 7
MAX_DOTNET  = 4

# ─── RSS FEEDS ─────────────────────────────────────────────────────────────────

AI_FEEDS = [
    ("TechCrunch",    "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge",     "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat",   "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica",  "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Wired",         "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("MIT Tech Rev.", "https://www.technologyreview.com/feed/"),
]

DOTNET_FEEDS = [
    ("MS .NET Blog",  "https://devblogs.microsoft.com/dotnet/feed/"),
    ("MS DevBlogs",   "https://devblogs.microsoft.com/feed/"),
    ("Hanselman",     "https://feeds.hanselman.com/ScottHanselman"),
]

# ─── LABEL DETECTION ───────────────────────────────────────────────────────────

LABEL_RULES = [
    ("breaking",   r"\bbreaking\b|\burgent\b|\bexclusive\b"),
    ("security",   r"\bsecurity\b|\bvulnerabilit\b|\bCVE\b|\bpatch\b|\bzero.?day\b|\bexploit\b"),
    ("funding",    r"\bfunding\b|\braised?\b|\bbillion\b|\bmillion\b|\binvestment\b|\bvaluation\b"),
    ("models",     r"\bmodel\b|\bGPT\b|\bClaude\b|\bGemini\b|\bLLM\b|\bparameter\b|\brelease\b"),
    ("research",   r"\bresearch\b|\bpaper\b|\bstudy\b|\bscientist\b|\buniversit\b|\bNature\b"),
    ("hardware",   r"\bchip\b|\bGPU\b|\bhardware\b|\bNvidia\b|\bprocessor\b|\bdevice\b"),
    ("enterprise", r"\benterprise\b|\bbusiness\b|\bcompan\b|\bstartup\b|\bproductivit\b"),
    ("release",    r"\bannouncing\b|\blaunching\b|\bnew\b|\bships?\b|\bavailable\b|\bupdate\b"),
    ("tools",      r"\bvisual studio\b|\bVS Code\b|\bIDE\b|\btooling\b|\bextension\b|\bplugin\b"),
    ("update",     r"\bupdate\b|\bservicing\b|\bfix\b|\bimprove\b|\benhance\b"),
]

def detect_label(text):
    text_lower = text.lower()
    for label, pattern in LABEL_RULES:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return label
    return "update"

# ─── FEED FETCHING ─────────────────────────────────────────────────────────────

def fetch_entries(feeds, max_items):
    entries = []
    seen_titles = set()
    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                summary = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                summary = re.sub(r"\s+", " ", summary)
                if len(summary) > 280:
                    summary = summary[:277].rsplit(" ", 1)[0] + "…"
                entries.append({
                    "title":   title,
                    "url":     entry.get("link", "#"),
                    "summary": summary,
                    "source":  source,
                    "label":   detect_label(title + " " + summary),
                })
                if len(entries) >= max_items:
                    return entries
        except Exception as e:
            print(f"  Warning: could not fetch {url}: {e}")
    return entries[:max_items]

# ─── LABEL COLOUR MAP ──────────────────────────────────────────────────────────

LABEL_STYLES = {
    "breaking":   ("rgba(239,68,68,0.15)",   "#f87171"),
    "funding":    ("rgba(251,191,36,0.15)",  "#fbbf24"),
    "models":     ("rgba(167,139,250,0.15)", "#a78bfa"),
    "enterprise": ("rgba(52,211,153,0.15)",  "#34d399"),
    "hardware":   ("rgba(96,165,250,0.15)",  "#60a5fa"),
    "research":   ("rgba(244,114,182,0.15)", "#f472b6"),
    "security":   ("rgba(239,68,68,0.15)",   "#f87171"),
    "release":    ("rgba(96,165,250,0.15)",  "#60a5fa"),
    "update":     ("rgba(52,211,153,0.15)",  "#34d399"),
    "tools":      ("rgba(251,191,36,0.15)",  "#fbbf24"),
}

def label_style(label):
    bg, color = LABEL_STYLES.get(label, ("rgba(100,100,130,0.15)", "#aaaacc"))
    return f'background:{bg};color:{color}'

# ─── CARD BUILDER ──────────────────────────────────────────────────────────────

def build_card(entry, highlight_class=""):
    label    = entry["label"]
    title    = escape(entry["title"])
    summary  = escape(entry["summary"])
    url      = entry["url"]
    source   = escape(entry["source"])
    l_style  = label_style(label)
    h_class  = f' {highlight_class}' if highlight_class else ''
    return f"""
  <div class="card{h_class}">
    <span class="card-label" style="{l_style}">{label.upper()}</span>
    <h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
    <p>{summary}</p>
    <div class="source"><a href="{url}" target="_blank" rel="noopener">{source}</a></div>
  </div>"""

# ─── HTML BUILDER ──────────────────────────────────────────────────────────────

def build_html(ai_entries, dotnet_entries):
    today       = datetime.now().strftime("%A, %B %-d, %Y")
    ai_cards    = "\n".join(build_card(e, "highlight-ai" if i == 0 else "")
                            for i, e in enumerate(ai_entries))
    dotnet_cards = "\n".join(build_card(e, "highlight-dotnet" if i == 0 else "")
                             for i, e in enumerate(dotnet_entries))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Briefing — {today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0f0f13;--surface:#18181f;--border:#2a2a38;--text:#e8e8ed;
    --text-muted:#8888a0;--accent-ai:#a78bfa;--accent-ai-dim:rgba(167,139,250,0.12);
    --accent-dotnet:#60a5fa;--accent-dotnet-dim:rgba(96,165,250,0.12);
    --accent-green:#34d399;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;min-height:100vh}}
  .container{{max-width:900px;margin:0 auto;padding:40px 24px 80px}}
  .header{{text-align:center;margin-bottom:56px;padding-bottom:40px;border-bottom:1px solid var(--border)}}
  .header-label{{display:inline-block;font-size:11px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:var(--text-muted);margin-bottom:16px;background:var(--surface);padding:6px 16px;border-radius:20px;border:1px solid var(--border)}}
  .header h1{{font-family:'Playfair Display',serif;font-size:clamp(36px,6vw,56px);font-weight:800;letter-spacing:-1px;margin-bottom:12px;background:linear-gradient(135deg,#e8e8ed 0%,#a0a0b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .header-date{{font-size:15px;color:var(--text-muted)}}
  .header-date span{{color:var(--accent-green);font-weight:500}}
  .section-header{{display:flex;align-items:center;gap:14px;margin-bottom:28px;margin-top:56px}}
  .section-icon{{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}}
  .section-icon.ai{{background:var(--accent-ai-dim)}}.section-icon.dotnet{{background:var(--accent-dotnet-dim)}}
  .section-header h2{{font-family:'Playfair Display',serif;font-size:28px;font-weight:700;letter-spacing:-0.5px}}
  .section-header h2.ai-title{{color:var(--accent-ai)}}.section-header h2.dotnet-title{{color:var(--accent-dotnet)}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px;margin-bottom:16px;transition:border-color 0.2s,transform 0.2s}}
  .card:hover{{border-color:#3a3a4f;transform:translateY(-1px)}}
  .card-label{{display:inline-block;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:4px 10px;border-radius:6px;margin-bottom:14px}}
  .card h3{{font-size:18px;font-weight:700;margin-bottom:10px;line-height:1.4}}
  .card h3 a{{color:inherit;text-decoration:none;transition:opacity 0.15s}}
  .card h3 a:hover{{opacity:0.75;text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}}
  .card p{{font-size:14px;color:var(--text-muted);line-height:1.75}}
  .card .source{{margin-top:14px;font-size:12px;display:flex;align-items:center;gap:6px}}
  .card .source a{{color:#7070a0;text-decoration:none}}.card .source a:hover{{color:#a0a0c0;text-decoration:underline}}
  .card.highlight-ai{{border-color:rgba(167,139,250,0.25);background:linear-gradient(135deg,rgba(167,139,250,0.06) 0%,var(--surface) 100%)}}
  .card.highlight-dotnet{{border-color:rgba(96,165,250,0.25);background:linear-gradient(135deg,rgba(96,165,250,0.06) 0%,var(--surface) 100%)}}
  .divider{{height:1px;background:var(--border);margin:48px 0}}
  .footer{{text-align:center;padding-top:32px;border-top:1px solid var(--border);margin-top:56px}}
  .footer p{{font-size:12px;color:#444460}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
  .card{{animation:fadeUp 0.5s ease both}}
  @media(max-width:600px){{.container{{padding:24px 16px 60px}}.card{{padding:20px}}}}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div class="header-label">Daily Briefing</div>
    <h1>Morning Briefing</h1>
    <p class="header-date">{today} &mdash; Dublin, Ireland &bull; <span>Live</span></p>
  </header>

  <div class="section-header">
    <div class="section-icon ai">&#x1F9E0;</div>
    <h2 class="ai-title">Artificial Intelligence</h2>
  </div>
  {ai_cards}

  <div class="divider"></div>

  <div class="section-header">
    <div class="section-icon dotnet">&#x2699;&#xFE0F;</div>
    <h2 class="dotnet-title">.NET &amp; C#</h2>
  </div>
  {dotnet_cards}

  <footer class="footer">
    <p>Gabo's Morning Briefing &bull; Auto-generated on {today} &bull; Powered by Claude</p>
  </footer>
</div>
</body>
</html>"""

# ─── EMAIL SENDER ──────────────────────────────────────────────────────────────

def send_email(html_content):
    today = datetime.now().strftime("%A, %B %-d, %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☕ Morning Briefing — {today}"
    msg["From"]    = "Gabo's Briefing <a4ff7a001@smtp-brevo.com>"
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

    print("📡 Fetching .NET news...")
    dotnet_entries = fetch_entries(DOTNET_FEEDS, MAX_DOTNET)
    print(f"   Got {len(dotnet_entries)} articles")

    print("🔨 Building HTML...")
    html_content = build_html(ai_entries, dotnet_entries)

    print("📧 Sending email...")
    send_email(html_content)
