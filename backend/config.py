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

# ── Tiers ──
# "base" is the entry point. Pro/Elite are bundles (or upgrade targets).

TIER_CONFIG = {
    "base": {
        "price":      0.75,
        "label":      "Base",
        "model":      "gpt-4o-mini",
        "max_tokens": 3500,
        "tavily_results": 5,
        "apis": [
            "apollo_org", "builtwith", "firecrawl_home", "tavily", "openai",
        ],
        "description": "Company snapshot, tech stack, timing signals, deal risks, talking points, and deep insights.",
    },
    "pro": {
        "price":      1.75,
        "label":      "Pro",
        "model":      "gpt-4o",
        "max_tokens": 6000,
        "tavily_results": 5,
        "apis": [
            "apollo_org", "apollo_people", "hunter", "builtwith",
            "firecrawl_home", "firecrawl_careers",
            "tavily", "tavily_hiring",
            "openai",
        ],
        "description": "Full intel + hiring pain + decision-makers + deal risks + battle plan + deep insights.",
    },
    "elite": {
        "price":      3.25,
        "label":      "Elite",
        "model":      "gpt-4o",
        "max_tokens": 10000,
        "tavily_results": 10,
        "apis": [
            "apollo_org", "apollo_people", "hunter", "builtwith",
            "firecrawl_home", "firecrawl_careers", "firecrawl_blog",
            "tavily", "tavily_hiring", "tavily_competitors",
            "openai",
        ],
        "description": "Deep research: initiatives, competitor displacement, timing triangulation.",
    },
}

TIER_ORDER = ["base", "pro", "elite"]

# ── Add-ons (purchasable individually after a base report) ──

ADDONS = {
    "hiring_pain": {
        "label":   "Hiring Pain Analysis",
        "price":   0.40,
        "apis":    ["firecrawl_careers", "tavily_hiring"],
        "icon":    "fire",
        "teaser":  "Scrapes their careers page + hiring signals to reveal problems they're actively throwing money at",
    },
    "decision_makers": {
        "label":   "Decision Maker Intel",
        "price":   0.50,
        "apis":    ["apollo_people", "hunter"],
        "icon":    "people",
        "teaser":  "Key people with verified emails, tenure flags, and why each one matters for YOUR pitch",
    },
    "initiatives": {
        "label":   "Company Initiatives",
        "price":   0.35,
        "apis":    ["firecrawl_blog"],
        "icon":    "rocket",
        "teaser":  "Named projects & strategic priorities from blog and press — name-drop material for the call",
    },
    "competitor_intel": {
        "label":   "Competitor Displacement",
        "price":   0.45,
        "apis":    ["tavily_competitors"],
        "icon":    "swords",
        "teaser":  "Competitor research cross-referenced with their tech stack for displacement angles",
    },
}

# ── Upgrade pricing ──
# Upgrading costs (target − current) × (1 − discount).
# This makes upgrades cheaper than buying the higher tier outright.
UPGRADE_DISCOUNT = 0.20  # 20% off the difference


def get_upgrade_price(current_tier: str, target_tier: str) -> float:
    """Return the discounted price to upgrade from current_tier to target_tier."""
    cur = TIER_CONFIG[current_tier]["price"]
    tgt = TIER_CONFIG[target_tier]["price"]
    diff = tgt - cur
    if diff <= 0:
        return 0.0
    return round(diff * (1 - UPGRADE_DISCOUNT), 2)


def get_available_addons(current_tier: str, purchased_addons: list[str]) -> dict:
    """Return add-ons not already covered by the current tier or purchased."""
    tier_apis = set(TIER_CONFIG[current_tier]["apis"])
    available = {}
    for key, addon in ADDONS.items():
        # skip if already purchased
        if key in purchased_addons:
            continue
        # skip if all addon APIs are already in the tier
        if set(addon["apis"]).issubset(tier_apis):
            continue
        available[key] = addon
    return available


def get_available_upgrades(current_tier: str) -> dict:
    """Return tiers above the current one with discounted upgrade prices."""
    idx = TIER_ORDER.index(current_tier)
    upgrades = {}
    for tier_key in TIER_ORDER[idx + 1:]:
        cfg = TIER_CONFIG[tier_key]
        upgrades[tier_key] = {
            "label":       cfg["label"],
            "full_price":  cfg["price"],
            "upgrade_price": get_upgrade_price(current_tier, tier_key),
            "description": cfg["description"],
        }
    return upgrades


# ── App ──
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "briefbot.db")
AGENTMAIL_INBOX_ID = os.getenv("AGENTMAIL_INBOX_ID", "")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_KEY", "briefbot-owner-2026")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
