# BriefBot — AI Sales Briefing Agent

Pay-per-report sales intelligence agent powered by [Locus](https://beta.paywithlocus.com). Enter a company name, get a cross-referenced battle plan in 30 seconds. Start with a cheap Base report, then add only the sections you need.

## How It Works

1. User enters a company name + what they're selling
2. Agent cross-references 6-10 live data sources in parallel (Apollo, Hunter, BuiltWith, Firecrawl, Tavily)
3. GPT-4o synthesises a personalised sales briefing
4. User can upgrade individual sections or the full tier after seeing results

## Pricing Model

| Plan | Price | What You Get |
|------|-------|--------------|
| Base | $0.75 | Company snapshot, tech stack, news, talking points |
| Pro Bundle | $1.75 | + Hiring pain detector, decision-maker map, tech displacement |
| Elite Bundle | $3.25 | + Blog/initiative detection, competitor displacement, timing triangulation |

**Add-ons** (after Base report):

| Add-on | Price |
|--------|-------|
| Hiring Pain Analysis | $0.40 |
| Decision Maker Intel | $0.50 |
| Company Initiatives | $0.35 |
| Competitor Displacement | $0.45 |

**Upgrades** are discounted (20% off the difference vs buying the higher tier outright).

## Quick Start

### Prerequisites

- Python 3.12+
- A Locus API key saved at `~/.config/locus/credentials.json`:
  ```json
  {
    "api_key": "claw_...",
    "api_base": "https://beta-api.paywithlocus.com/api"
  }
  ```

### Setup (one-time)

```bash
cd ~/Desktop/Course_S6/agent_locus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### Stop

`Ctrl + C` in the terminal.

## Environment Variables (optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOCUS_API_KEY` | Reads from `~/.config/locus/credentials.json` | Locus API authentication |
| `SERVER_URL` | `http://localhost:8000` | Checkout redirect URLs |
| `AGENTMAIL_INBOX_ID` | (empty) | Set to enable email delivery of reports |

## Project Structure

```
agent_locus/
  backend/
    main.py          # FastAPI app — routes, checkout, addon/upgrade endpoints
    config.py        # Tiers, add-ons, pricing, upgrade logic
    pipeline.py      # Parallel data gathering + synthesis (full, addon, upgrade)
    prompts.py       # Tier templates + per-addon focused prompts
    database.py      # SQLite schema + CRUD
    locus_client.py  # Async wrapper for Locus Beta API
  frontend/
    index.html       # Landing page — tier selector + order form
    report.html      # Report viewer — section cards, add-on buttons, upgrade banners
    dashboard.html   # Operator dashboard — revenue, costs, profit margin
  requirements.txt
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/orders` | Create order + Locus checkout session |
| GET | `/api/orders/{id}` | Poll order status (checks payment + pending addons) |
| GET | `/api/orders/{id}/options` | Available add-ons + upgrade prices for this order |
| POST | `/api/orders/{id}/addon` | Purchase an individual add-on section |
| POST | `/api/orders/{id}/upgrade` | Upgrade to a higher tier |
| POST | `/api/orders/{id}/send-email` | Email report via AgentMail |
| GET | `/api/orders` | List all orders |
| GET | `/api/dashboard` | Dashboard stats + wallet balance |

## Tech Stack

- **Backend:** FastAPI + SQLite + httpx
- **Frontend:** Vanilla HTML + Tailwind CSS + marked.js
- **APIs:** Apollo, Hunter, BuiltWith, Firecrawl, Tavily, OpenAI (all via Locus wrapped APIs)
- **Payments:** Locus Checkout (USDC on Base)
- **Email:** AgentMail (via Locus x402)

## Built For

Locus Paygentic Hackathon — [beta.paywithlocus.com](https://beta.paywithlocus.com)
