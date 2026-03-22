# ─── SOURCES ───────────────────────────────────────────────────────────────────
# All RSS feed URLs and static Dublin events for each section.
# Edit this file to add, remove, or update sources without touching section logic.

# ─── AI FEEDS ──────────────────────────────────────────────────────────────────

AI_FEEDS = [
    ("TechCrunch",         "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge",          "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat",        "https://venturebeat.com/category/ai/feed/"),
    ("Wired",              "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("Zdnet",              "https://www.zdnet.com/topic/artificial-intelligence/rss.xml"),
    ("Financial Times", "https://www.ft.com/artificial-intelligence?format=rss"),
    ("AINEWS",              "https://www.artificialintelligence-news.com/feed/"),

]

AI_DEV_FEEDS = [
    ("LogRocket",              "https://blog.logrocket.com/feed/"),
    ("The Pragmatic Engineer", "https://newsletter.pragmaticengineer.com/feed"),
    ("SD Times",               "https://sdtimes.com/feed/"),
    ("InfoQ",                  "https://www.infoq.com/ai/rss"),
    ("Dev.to AI",              "https://dev.to/feed/tag/ai"),
]

# ─── .NET & C# FEEDS ───────────────────────────────────────────────────────────

DOTNET_FEEDS = [
    ("MS .NET Blog",   "https://devblogs.microsoft.com/dotnet/feed/"),
    ("MS DevBlogs",    "https://devblogs.microsoft.com/feed/"),    
    (".NET Ketchup",   "https://dotnetketchup.com/feed"),
    (".NET Ramblings",   "https://www.dotnetramblings.com/index.xml"),

]

# ─── DUBLIN AI EVENT FEEDS ─────────────────────────────────────────────────────

AI_EVENT_FEEDS = [
    # Dublin Meetup groups — AI / ML / Data Science
    ("Dublin AI Meetup",        "https://www.meetup.com/artificial-intelligence-ai-meetup-group-dublin/events/rss/"),
    ("Dublin Data Science",     "https://www.meetup.com/dublin-data-science/events/rss/"),
    ("ML Dublin",               "https://www.meetup.com/machine-learning-meetup-dublin/events/rss/"),
    ("Dublin AI Hub",           "https://www.meetup.com/dublin-ai-hub/events/rss/"),
    ("Dublin NLP",              "https://www.meetup.com/Dublin-nlp/events/rss/"),
    ("AI Ireland Meetup",       "https://www.meetup.com/ai-ireland/events/rss/"),
    # Eventbrite keyword search (Dublin, AI)
    ("Eventbrite AI Dublin",    "https://www.eventbrite.ie/rss/find/?q=AI+Dublin&sort=date&country=IE&city=Dublin"),
    ("Eventbrite ML Dublin",    "https://www.eventbrite.ie/rss/find/?q=machine+learning+Dublin&sort=date&country=IE"),
]

AI_EVENT_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "llm", "deep learning",
    "neural", "data science", "nlp", "generative", "gpt", "chatgpt", "langchain",
    "vector", "embedding", "rag", "agents", "openai", "anthropic",
]

# ─── DUBLIN .NET EVENT FEEDS ────────────────────────────────────────────────────

DOTNET_EVENT_FEEDS = [
    # Dublin Meetup groups — .NET / C# / Microsoft
    (".NET Dublin",             "https://www.meetup.com/dotnet-dublin/events/rss/"),
    ("DotNet Dublin Alt",       "https://www.meetup.com/DotNetDublin/events/rss/"),
    ("Dublin .NET Dev",         "https://www.meetup.com/DublinNET/events/rss/"),
    ("Azure Dublin",            "https://www.meetup.com/Dublin-Azure-Meetup/events/rss/"),
    ("Dublin Dev",              "https://www.meetup.com/Dublin-Dev/events/rss/"),
    # Eventbrite keyword search (Dublin, .NET)
    ("Eventbrite .NET Dublin",  "https://www.eventbrite.ie/rss/find/?q=dotnet+Dublin&sort=date&country=IE"),
    ("Eventbrite Azure Dublin", "https://www.eventbrite.ie/rss/find/?q=Azure+Dublin&sort=date&country=IE"),
]

DOTNET_EVENT_KEYWORDS = [
    ".net", "dotnet", "c#", "csharp", "asp.net", "blazor", "maui",
    "azure", "microsoft", "ef core", "entity framework", "rider", "visual studio",
]

# ─── FINANCIAL NEWS FEEDS ──────────────────────────────────────────────────────
# Add your financial news RSS sources here.

FINANCIAL_NEWS_FEEDS = [
    # Add sources here, e.g.:
    ("CNBC Finance",     "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
     ("Seeking Alpha",    "https://seekingalpha.com/feed.xml"),
     ("BitFinanzas",    "https://bitfinanzas.com/feed"),
     ("Cointelegraph",    "https://cointelegraph.com/rss"),
     ("MorningStar",    "https://global.morningstar.com/es/mercados"),
     ("Bitcoinist",    "https://bitcoinist.com/category/ethereum/feed/"),

]

# ─── FINANCIAL INDICATORS ──────────────────────────────────────────────────────
# Tickers shown in the Financials section.
# Format: (display name, Yahoo Finance ticker, category)
# Categories: crypto | index | etf | commodity | trust | fx

FINANCIAL_INDICATORS = [
    # Crypto
    ("Bitcoin",        "BTC-USD",   "crypto"),
    ("Ethereum",       "ETH-USD",   "crypto"),
    # Volatility & indices
    ("VIX",            "^VIX",      "index"),
    ("SPY",            "SPY",       "etf"),
    ("QQQ",            "QQQ",       "etf"),
    # Commodities
    ("Gold (GLD)",     "GLD",       "commodity"),
    ("Silver (SLV)",   "SLV",       "commodity"),
    ("Crude Oil",      "CL=F",      "commodity"),   # WTI front-month (CL1!)
    ("Natural Gas",    "NG=F",      "commodity"),
    # FX
    ("DXY",            "DX-Y.NYB",  "fx"),          # US Dollar Index
    ("EUR/USD",        "EURUSD=X",  "fx"),
    # Bonds & rates
    ("US 10Y Yield",   "^TNX",      "bond"),
    ("US 30Y Yield",   "^TYX",      "bond"),        # closest to 20Y on Yahoo Finance
    ("TLT",            "TLT",       "etf"),
    # UK Investment Trusts (prices in GBX — pence)
    ("JGGI",           "JGGI.L",    "trust"),
    ("FCIT",           "FCIT.L",    "trust"),
    ("PCT",            "PCT.L",     "trust"),
    ("JAM",            "JAM.L",     "trust"),
]

