import json
import os
from pathlib import Path

# ── Locus API ──
LOCUS_API_KEY = os.getenv("LOCUS_API_KEY", "")
LOCUS_API_BASE = "https://beta-api.paywithlocus.com/api"

if not LOCUS_API_KEY:
    _creds = Path.home() / ".config" / "locus" / "credentials.json"
    if _creds.exists():
        with open(_creds) as f:
            _c = json.load(f)
            LOCUS_API_KEY = _c.get("api_key", "")
            LOCUS_API_BASE = _c.get("api_base", LOCUS_API_BASE)

# ── App ──
TIER_CONFIG = {
    "starter": {
        "price":      0.75,
        "label":      "Starter",
        "model":      "gpt-4o-mini",
        "max_tokens": 2000,
        "tavily_results": 5,
        "apis": ["apollo_org", "tavily", "openai"],
        "description": "Company snapshot + news. Fast & affordable.",
    },
    "pro": {
        "price":      1.50,
        "label":      "Pro",
        "model":      "gpt-4o",
        "max_tokens": 4000,
        "tavily_results": 5,
        "apis": ["apollo_org", "apollo_people", "hunter", "builtwith", "firecrawl", "tavily", "openai"],
        "description": "Full 6-source intel + GPT-4o synthesis.",
    },
    "elite": {
        "price":      3.00,
        "label":      "Elite",
        "model":      "gpt-4o",
        "max_tokens": 8000,
        "tavily_results": 10,
        "apis": ["apollo_org", "apollo_people", "hunter", "builtwith", "firecrawl", "tavily", "tavily_competitors", "openai"],
        "description": "Deep research: 10 news results, competitor search, 8k token report.",
    },
}
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "briefbot.db")
AGENTMAIL_INBOX_ID = os.getenv("AGENTMAIL_INBOX_ID", "")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
