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
REPORT_PRICE_USDC = 1.50
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "briefbot.db")
AGENTMAIL_INBOX_ID = os.getenv("AGENTMAIL_INBOX_ID", "")
