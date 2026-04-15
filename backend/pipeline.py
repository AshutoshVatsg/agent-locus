"""
Multi-stage agent pipeline with add-on and upgrade support.

- run_pipeline():  Full report for a tier (base / pro / elite)
- run_addon():     Single section add-on (appends to existing report)
- run_upgrade():   Upgrade to higher tier (runs missing APIs + full re-synthesis)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from locus_client import LocusClient
from prompts import (
    SYNTHESIS_SYSTEM, ADDON_SYSTEM,
    build_synthesis_prompt, build_addon_prompt,
)
from database import update_order, get_order
from config import TIER_CONFIG, ADDONS

log = logging.getLogger("pipeline")

# Estimated per-call costs in USDC
COSTS = {
    "apollo_org":    0.008,
    "apollo_people": 0.005,
    "hunter":        0.013,
    "builtwith":     0.015,
    "firecrawl":     0.005,
    "tavily":        0.090,
    "openai":        0.050,
}


# ═══════════════════════════════════════════════════════════════════
#  FULL PIPELINE (initial report for any tier)
# ═══════════════════════════════════════════════════════════════════

async def run_pipeline(order_id: str, company: str, domain: str,
                       context: str, tier: str = "base"):
    locus = LocusClient()
    costs: dict[str, float] = {}
    cfg = TIER_CONFIG.get(tier, TIER_CONFIG["base"])
    apis = cfg["apis"]

    try:
        if not domain:
            domain = await _resolve_domain(locus, company)
            costs["apollo_org_resolve"] = COSTS["apollo_org"]

        url = f"https://{domain}" if domain else None

        data = await _gather_all(locus, apis, company, domain, url, cfg, costs)

        # persist raw data
        update_order(order_id,
            company_domain=domain or "",
            company_data=json.dumps(data["company"], default=str),
            people_data=json.dumps(data["people_combined"], default=str),
            tech_data=json.dumps(data["tech"], default=str),
            website_data=json.dumps(data["website"], default=str),
            careers_data=json.dumps(data["careers"], default=str),
            blog_data=json.dumps(data["blog"], default=str),
            news_data=json.dumps(data["news"], default=str),
            hiring_data=json.dumps(data["hiring"], default=str),
            competitor_data=json.dumps(data["competitor"], default=str),
        )

        # synthesise
        report = await _synthesise_full(locus, cfg, company, context, data, costs)

        total_cost = round(sum(costs.values()), 4)
        update_order(order_id,
            status="COMPLETED",
            report=report,
            total_cost=total_cost,
            cost_breakdown=json.dumps(costs),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("Order %s (%s) completed — cost $%.4f", order_id, tier, total_cost)

    except Exception as exc:
        log.exception("Pipeline failed for %s", order_id)
        update_order(order_id, status="FAILED", error=str(exc))


# ═══════════════════════════════════════════════════════════════════
#  ADD-ON PIPELINE (one section, appended)
# ═══════════════════════════════════════════════════════════════════

async def run_addon(order_id: str, addon_key: str):
    """Run a single add-on: fetch its APIs, synthesise one section, append."""
    locus = LocusClient()
    addon = ADDONS[addon_key]
    order = get_order(order_id)

    company = order["company_name"]
    domain = order["company_domain"]
    context = order["context"]
    url = f"https://{domain}" if domain else None

    costs: dict[str, float] = json.loads(order.get("cost_breakdown") or "{}")
    new_data = {}

    try:
        # fetch only the APIs this add-on needs
        tasks = {}
        for api in addon["apis"]:
            tasks[api] = _fetch_api(locus, api, company, domain, url)

        results = await asyncio.gather(*tasks.values())
        api_results = dict(zip(tasks.keys(), results))
        existing_people = _load_json(order.get("people_data"), {})
        if not any(_call_succeeded(result) for result in api_results.values()):
            raise RuntimeError(f"All Locus add-on API calls failed for '{addon_key}'")

        # map API results to data keys + track costs
        for api, result in api_results.items():
            if not _call_succeeded(result):
                continue

            cost_key = _api_cost_key(api)
            costs[f"addon_{addon_key}_{cost_key}"] = COSTS.get(cost_key, 0.01)

            if api == "firecrawl_careers":
                new_data["careers_data"] = result
                update_order(order_id, careers_data=json.dumps(result, default=str))
            elif api == "tavily_hiring":
                new_data["hiring_data"] = result
                update_order(order_id, hiring_data=json.dumps(result, default=str))
            elif api == "apollo_people":
                new_data["people_data"] = result
            elif api == "hunter":
                new_data["hunter_data"] = result
            elif api == "firecrawl_blog":
                new_data["blog_data"] = result
                update_order(order_id, blog_data=json.dumps(result, default=str))
            elif api == "tavily_competitors":
                new_data["competitor_data"] = result
                update_order(order_id, competitor_data=json.dumps(result, default=str))

        merged_people = _merge_people_data(
            existing_people,
            apollo=new_data.get("people_data"),
            hunter=new_data.get("hunter_data"),
        )
        if merged_people != existing_people:
            update_order(order_id, people_data=json.dumps(merged_people, default=str))

        # synthesise just this section
        prompt = build_addon_prompt(addon_key, company, context, order, new_data)
        synthesis = await locus.openai_chat(
            system=ADDON_SYSTEM,
            user=prompt,
            model="gpt-4o",
            max_tokens=2000,
        )
        costs[f"addon_{addon_key}_openai"] = COSTS["openai"]

        section_md = _extract_report(synthesis)

        # append to existing report
        existing_report = order.get("report") or ""
        updated_report = existing_report.rstrip() + "\n\n" + section_md

        # update purchased addons list
        purchased = json.loads(order.get("addons_purchased") or "[]")
        if addon_key not in purchased:
            purchased.append(addon_key)

        total_cost = round(sum(costs.values()), 4)
        new_revenue = (order.get("revenue") or 0) + addon["price"]

        update_order(order_id,
            status="COMPLETED",
            report=updated_report,
            total_cost=total_cost,
            cost_breakdown=json.dumps(costs),
            revenue=new_revenue,
            addons_purchased=json.dumps(purchased),
            pending_action="",
        )
        log.info("Add-on '%s' for order %s completed", addon_key, order_id)

    except Exception as exc:
        log.exception("Add-on '%s' failed for %s", addon_key, order_id)
        update_order(order_id, status="COMPLETED", pending_action="", error=str(exc))


# ═══════════════════════════════════════════════════════════════════
#  UPGRADE PIPELINE (re-run with higher tier)
# ═══════════════════════════════════════════════════════════════════

async def run_upgrade(order_id: str, target_tier: str):
    """Upgrade to a higher tier: run missing APIs, then full re-synthesis."""
    locus = LocusClient()
    order = get_order(order_id)
    cfg = TIER_CONFIG[target_tier]

    company = order["company_name"]
    domain = order["company_domain"]
    context = order["context"]
    url = f"https://{domain}" if domain else None

    old_apis = set(TIER_CONFIG.get(order.get("tier", "base"), TIER_CONFIG["base"])["apis"])
    new_apis = set(cfg["apis"]) - old_apis - {"openai"}

    costs: dict[str, float] = json.loads(order.get("cost_breakdown") or "{}")

    try:
        # fetch only the NEW APIs
        if new_apis:
            tasks = {}
            for api in new_apis:
                tasks[api] = _fetch_api(locus, api, company, domain, url)

            results = await asyncio.gather(*tasks.values())
            api_results = dict(zip(tasks.keys(), results))
            existing_people = _load_json(order.get("people_data"), {})
            apollo_result = None
            hunter_result = None
            if not any(_call_succeeded(result) for result in api_results.values()):
                raise RuntimeError(f"All Locus upgrade API calls failed for tier '{target_tier}'")

            for api, result in api_results.items():
                if not _call_succeeded(result):
                    continue

                cost_key = _api_cost_key(api)
                costs[f"upgrade_{cost_key}"] = COSTS.get(cost_key, 0.01)

                if api == "apollo_people":
                    apollo_result = result
                elif api == "hunter":
                    hunter_result = result
                elif api == "firecrawl_careers":
                    update_order(order_id, careers_data=json.dumps(result, default=str))
                elif api == "firecrawl_blog":
                    update_order(order_id, blog_data=json.dumps(result, default=str))
                elif api == "tavily_hiring":
                    update_order(order_id, hiring_data=json.dumps(result, default=str))
                elif api == "tavily_competitors":
                    update_order(order_id, competitor_data=json.dumps(result, default=str))

            merged_people = _merge_people_data(
                existing_people,
                apollo=apollo_result,
                hunter=hunter_result,
            )
            if merged_people != existing_people:
                update_order(order_id, people_data=json.dumps(merged_people, default=str))

        # re-read order with all updated data
        order = get_order(order_id)

        data = {
            "company":        json.loads(order.get("company_data") or "{}"),
            "people_combined": json.loads(order.get("people_data") or "{}"),
            "tech":           json.loads(order.get("tech_data") or "{}"),
            "website":        json.loads(order.get("website_data") or "{}"),
            "careers":        json.loads(order.get("careers_data") or "{}"),
            "blog":           json.loads(order.get("blog_data") or "{}"),
            "news":           json.loads(order.get("news_data") or "{}"),
            "hiring":         json.loads(order.get("hiring_data") or "{}"),
            "competitor":     json.loads(order.get("competitor_data") or "{}"),
        }

        # full re-synthesis with the target tier template
        report = await _synthesise_full(locus, cfg, company, context, data, costs)

        from config import get_upgrade_price
        upgrade_price = get_upgrade_price(order.get("tier", "base"), target_tier)
        new_revenue = (order.get("revenue") or 0) + upgrade_price
        total_cost = round(sum(costs.values()), 4)

        update_order(order_id,
            status="COMPLETED",
            tier=target_tier,
            report=report,
            total_cost=total_cost,
            cost_breakdown=json.dumps(costs),
            revenue=new_revenue,
            pending_action="",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("Upgrade to %s for order %s completed", target_tier, order_id)

    except Exception as exc:
        log.exception("Upgrade to %s failed for %s", target_tier, order_id)
        update_order(order_id, status="COMPLETED", pending_action="", error=str(exc))


# ═══════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════

async def _gather_all(locus, apis, company, domain, url, cfg, costs):
    """Run all tier APIs in parallel and return a structured dict."""
    run = lambda api: api in apis
    has_domain = bool(domain)
    has_url = bool(url)

    results = await asyncio.gather(
        _safe(locus.apollo_org_enrichment(domain=domain, name=company)),
        _safe(locus.apollo_people_search(domain))            if run("apollo_people") and has_domain else _noop(),
        _safe(locus.hunter_domain_search(domain))            if run("hunter") and has_domain        else _noop(),
        _safe(locus.builtwith_lookup(domain))                if run("builtwith") and has_domain     else _noop(),
        _safe(locus.firecrawl_scrape(url))                   if run("firecrawl_home") and has_url   else _noop(),
        _safe(locus.firecrawl_scrape(f"{url}/careers"))      if run("firecrawl_careers") and has_url else _noop(),
        _safe(locus.firecrawl_scrape(f"{url}/blog"))         if run("firecrawl_blog") and has_url   else _noop(),
        _safe(locus.tavily_search(
            f"{company} latest news funding product launch",
            max_results=cfg["tavily_results"],
            topic="news")),
        _safe(locus.tavily_search(
            f"{company} hiring engineers job openings team growth",
            max_results=5))                                   if run("tavily_hiring")       else _noop(),
        _safe(locus.tavily_search(
            f"{company} competitors alternatives comparison review",
            max_results=5))                                   if run("tavily_competitors")  else _noop(),
    )

    (company_data, people_data, hunter_data, tech_data,
     website_data, careers_data, blog_data,
     news_data, hiring_data, competitor_data) = results

    selected_results = [company_data, news_data]
    if run("apollo_people") and has_domain:
        selected_results.append(people_data)
    if run("hunter") and has_domain:
        selected_results.append(hunter_data)
    if run("builtwith") and has_domain:
        selected_results.append(tech_data)
    if run("firecrawl_home") and has_url:
        selected_results.append(website_data)
    if run("firecrawl_careers") and has_url:
        selected_results.append(careers_data)
    if run("firecrawl_blog") and has_url:
        selected_results.append(blog_data)
    if run("tavily_hiring"):
        selected_results.append(hiring_data)
    if run("tavily_competitors"):
        selected_results.append(competitor_data)

    if not any(_call_succeeded(result) for result in selected_results):
        raise RuntimeError("All Locus data-gathering calls failed")

    # track costs
    if _call_succeeded(company_data):                          costs["apollo_org"] = COSTS["apollo_org"]
    if run("apollo_people") and has_domain and _call_succeeded(people_data):
        costs["apollo_people"] = COSTS["apollo_people"]
    if run("hunter") and has_domain and _call_succeeded(hunter_data):
        costs["hunter"] = COSTS["hunter"]
    if run("builtwith") and has_domain and _call_succeeded(tech_data):
        costs["builtwith"] = COSTS["builtwith"]
    if run("firecrawl_home") and has_url and _call_succeeded(website_data):
        costs["firecrawl_home"] = COSTS["firecrawl"]
    if run("firecrawl_careers") and has_url and _call_succeeded(careers_data):
        costs["firecrawl_careers"] = COSTS["firecrawl"]
    if run("firecrawl_blog") and has_url and _call_succeeded(blog_data):
        costs["firecrawl_blog"] = COSTS["firecrawl"]
    if _call_succeeded(news_data): costs["tavily_news"] = COSTS["tavily"]
    if run("tavily_hiring") and _call_succeeded(hiring_data):
        costs["tavily_hiring"] = COSTS["tavily"]
    if run("tavily_competitors") and _call_succeeded(competitor_data):
        costs["tavily_competitors"] = COSTS["tavily"]

    return {
        "company":        company_data,
        "people_combined": {"apollo": people_data, "hunter": hunter_data},
        "tech":           tech_data,
        "website":        website_data,
        "careers":        careers_data,
        "blog":           blog_data,
        "news":           news_data,
        "hiring":         hiring_data,
        "competitor":     competitor_data,
    }


async def _synthesise_full(locus, cfg, company, context, data, costs):
    """Run the synthesis LLM and return the markdown report."""
    user_prompt = build_synthesis_prompt(
        company=company, context=context,
        company_data=data["company"],
        people_data=data["people_combined"],
        tech_data=data["tech"],
        website_data=data["website"],
        careers_data=data["careers"],
        blog_data=data["blog"],
        news_data=data["news"],
        hiring_data=data["hiring"],
        competitor_data=data["competitor"],
        tier=cfg.get("tier_key") or _tier_key(cfg),
    )
    synthesis = await locus.openai_chat(
        system=SYNTHESIS_SYSTEM,
        user=user_prompt,
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
    )
    costs["openai"] = COSTS["openai"]
    return _extract_report(synthesis)


def _tier_key(cfg):
    """Reverse-lookup tier key from config."""
    for k, v in TIER_CONFIG.items():
        if v is cfg:
            return k
    return "base"


async def _fetch_api(locus, api, company, domain, url):
    """Fetch a single API by name. Used for add-ons and upgrades."""
    dispatch = {
        "apollo_people":      lambda: locus.apollo_people_search(domain),
        "hunter":             lambda: locus.hunter_domain_search(domain),
        "firecrawl_careers":  lambda: locus.firecrawl_scrape(f"{url}/careers"),
        "firecrawl_blog":     lambda: locus.firecrawl_scrape(f"{url}/blog"),
        "tavily_hiring":      lambda: locus.tavily_search(
            f"{company} hiring engineers job openings team growth", max_results=5),
        "tavily_competitors": lambda: locus.tavily_search(
            f"{company} competitors alternatives comparison review", max_results=5),
    }
    fn = dispatch.get(api)
    if fn:
        return await _safe(fn())
    return {}


def _api_cost_key(api: str) -> str:
    """Map API name to its cost dict key."""
    if api.startswith("firecrawl"):
        return "firecrawl"
    if api.startswith("tavily"):
        return "tavily"
    return api


async def _safe(coro):
    try:
        return await coro
    except Exception as exc:
        log.warning("Stage error: %s", exc)
        return {"error": str(exc)}


async def _noop():
    return {}


async def _resolve_domain(locus, company):
    try:
        r = await locus.apollo_org_enrichment(name=company)
        if r.get("success"):
            d = r.get("data", {}).get("organization", {}).get("primary_domain", "")
            if d:
                return d
    except Exception:
        pass
    return company.lower().replace(" ", "") + ".com"


def _extract_report(resp):
    if resp.get("success"):
        choices = resp.get("data", {}).get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
    return ("## Report Generation Failed\n\n"
            "The synthesis stage did not return a report. "
            "Raw intelligence data is still available.")


def _call_succeeded(result) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("success") is False:
        return False
    return "error" not in result


def _load_json(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _merge_people_data(existing, *, apollo=None, hunter=None):
    merged = dict(existing or {})
    if apollo is not None:
        merged["apollo"] = apollo
    if hunter is not None:
        merged["hunter"] = hunter
    return merged
