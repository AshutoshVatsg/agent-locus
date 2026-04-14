"""
Six-stage agent pipeline with tier support.

Stages 1-5 (data gathering) run in parallel.
Stage 6 (synthesis) runs after all data is collected.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from locus_client import LocusClient
from prompts import SYNTHESIS_SYSTEM, build_synthesis_prompt
from database import update_order
from config import TIER_CONFIG

log = logging.getLogger("pipeline")

# Estimated per-call costs in USDC (used for profit tracking)
COSTS = {
    "apollo_org":    0.008,
    "apollo_people": 0.005,
    "hunter":        0.013,
    "builtwith":     0.015,
    "firecrawl":     0.005,
    "tavily":        0.090,
    "openai":        0.050,
}


async def run_pipeline(order_id: str, company: str, domain: str, context: str, tier: str = "pro"):
    locus = LocusClient()
    costs: dict[str, float] = {}
    cfg = TIER_CONFIG.get(tier, TIER_CONFIG["pro"])
    apis = cfg["apis"]

    try:
        # ── resolve domain ──
        if not domain:
            domain = await _resolve_domain(locus, company)
            costs["apollo_org_resolve"] = COSTS["apollo_org"]

        url = f"https://{domain}" if domain else None

        # ── stages 1-5: parallel data gathering (based on tier) ──
        run_people   = "apollo_people" in apis and bool(domain)
        run_hunter   = "hunter"        in apis and bool(domain)
        run_builtwith= "builtwith"     in apis and bool(domain)
        run_firecrawl= "firecrawl"     in apis and bool(url)
        run_tavily_c = "tavily_competitors" in apis  # elite only

        (company_data, people_data, hunter_data,
         tech_data, website_data, news_data, competitor_data) = await asyncio.gather(
            _safe(locus.apollo_org_enrichment(domain=domain, name=company)),
            _safe(locus.apollo_people_search(domain))                       if run_people    else _noop(),
            _safe(locus.hunter_domain_search(domain))                       if run_hunter    else _noop(),
            _safe(locus.builtwith_lookup(domain))                           if run_builtwith else _noop(),
            _safe(locus.firecrawl_scrape(url))                              if run_firecrawl else _noop(),
            _safe(locus.tavily_search(f"{company} latest news funding", max_results=cfg["tavily_results"])),
            _safe(locus.tavily_search(f"{company} competitors alternatives", max_results=5)) if run_tavily_c else _noop(),
        )

        # track costs for stages that ran
        costs["apollo_org"] = COSTS["apollo_org"]
        if run_people:
            costs["apollo_people"] = COSTS["apollo_people"]
        if run_hunter:
            costs["hunter"] = COSTS["hunter"]
        if run_builtwith:
            costs["builtwith"] = COSTS["builtwith"]
        if run_firecrawl:
            costs["firecrawl"] = COSTS["firecrawl"]
        costs["tavily"] = COSTS["tavily"]
        if run_tavily_c:
            costs["tavily_competitors"] = COSTS["tavily"]

        people_combined = {"apollo": people_data, "hunter": hunter_data}

        # persist raw data
        update_order(order_id,
            company_domain=domain or "",
            company_data=json.dumps(company_data, default=str),
            people_data=json.dumps(people_combined, default=str),
            tech_data=json.dumps(tech_data, default=str),
            website_data=json.dumps(website_data, default=str),
            news_data=json.dumps(news_data, default=str),
        )

        # ── stage 6: synthesise report ──
        user_prompt = build_synthesis_prompt(
            company=company,
            context=context,
            company_data=company_data,
            people_data=people_combined,
            tech_data=tech_data,
            website_data=website_data,
            news_data=news_data,
            competitor_data=competitor_data if run_tavily_c else {},
            tier=tier,
        )

        synthesis = await locus.openai_chat(
            system=SYNTHESIS_SYSTEM,
            user=user_prompt,
            model=cfg["model"],
            max_tokens=cfg["max_tokens"],
        )
        costs["openai"] = COSTS["openai"]

        report = _extract_report(synthesis)
        total_cost = round(sum(costs.values()), 4)

        update_order(order_id,
            status="COMPLETED",
            report=report,
            total_cost=total_cost,
            cost_breakdown=json.dumps(costs),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("Order %s (%s tier) completed — cost $%.4f", order_id, tier, total_cost)

    except Exception as exc:
        log.exception("Pipeline failed for %s", order_id)
        update_order(order_id, status="FAILED", error=str(exc))


# ── helpers ──

async def _safe(coro):
    """Run a coroutine; return {} on failure instead of crashing the gather."""
    try:
        return await coro
    except Exception as exc:
        log.warning("Stage error: %s", exc)
        return {"error": str(exc)}


async def _noop():
    return {}


async def _resolve_domain(locus: LocusClient, company: str) -> str:
    """Use Apollo to find the company domain, fall back to a guess."""
    try:
        r = await locus.apollo_org_enrichment(name=company)
        if r.get("success"):
            org = r.get("data", {}).get("organization", {})
            d = org.get("primary_domain") or ""
            if d:
                return d
    except Exception:
        pass
    return company.lower().replace(" ", "") + ".com"


def _extract_report(resp: dict) -> str:
    """Pull the markdown text out of an OpenAI chat response."""
    if resp.get("success"):
        choices = resp.get("data", {}).get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
    return ("## Report Generation Failed\n\n"
            "The synthesis stage did not return a report. "
            "Raw intelligence data is still available.")
