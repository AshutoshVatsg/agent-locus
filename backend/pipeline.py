"""
Multi-stage agent pipeline with autonomous enrichment.

- run_pipeline():  Full report for a tier (base / pro / elite)
- run_addon():     Single section add-on (appends to existing report)
- run_upgrade():   Upgrade to higher tier (runs missing APIs + full re-synthesis)

The agent autonomously evaluates data quality after the initial API sweep
and spends additional USDC to fill gaps — the core "paygentic" behaviour.
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

# Maximum extra spend the agent is allowed per enrichment pass (USDC)
ENRICHMENT_BUDGET = {
    "base":  0.10,   # $0.75 tier — lean enrichment
    "pro":   0.20,   # $1.75 tier — moderate enrichment
    "elite": 0.40,   # $3.25 tier — aggressive enrichment
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

        # ── AUTONOMOUS ENRICHMENT ──
        # Agent evaluates data quality and spends to fill gaps
        enrichment_log = await _autonomous_enrich(
            locus, data, apis, company, domain, url, context, costs, tier,
        )
        if enrichment_log:
            log.info("Agent enrichment for %s: %d actions, $%.4f spent",
                     order_id, len(enrichment_log),
                     sum(e["cost"] for e in enrichment_log))

        # persist raw data
        update_order(order_id,
            enrichment_log=json.dumps(enrichment_log),
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
        report = await _synthesise_full(locus, cfg, company, context, data, costs,
                                        enrichment_log=enrichment_log)

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
        update_order(order_id, status="ADDON_FAILED", pending_action="",
                     error=f"Add-on '{addon_key}' failed: {exc}")


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
        update_order(order_id, status="UPGRADE_FAILED", pending_action="",
                     error=f"Upgrade to '{target_tier}' failed: {exc}")


# ═══════════════════════════════════════════════════════════════════
#  AUTONOMOUS ENRICHMENT ENGINE
# ═══════════════════════════════════════════════════════════════════

def _score_people(data) -> dict:
    """Score quality of people data. Returns {score: 0-10, issues: [...]}."""
    people = data.get("people_combined", {})
    apollo = people.get("apollo", {})
    hunter = people.get("hunter", {})
    issues = []

    # Check Apollo people
    apollo_people = []
    if isinstance(apollo, dict) and apollo.get("success"):
        apollo_people = (apollo.get("data", {}).get("people", [])
                         or apollo.get("data", {}).get("contacts", []))

    titled_count = 0
    for p in apollo_people:
        name = (p.get("first_name", "") or "").strip()
        title = (p.get("title", "") or "").strip()
        if name and title:
            titled_count += 1

    if not apollo_people:
        issues.append("No people found from Apollo")
    elif titled_count == 0:
        issues.append("People found but none have job titles")
    elif titled_count < 3:
        issues.append(f"Only {titled_count} people with titles (weak)")

    # Check Hunter emails
    hunter_emails = []
    if isinstance(hunter, dict) and hunter.get("success"):
        hunter_emails = hunter.get("data", {}).get("emails", [])

    if not hunter_emails:
        issues.append("No email contacts from Hunter")

    score = 10
    if not apollo_people:
        score -= 5
    elif titled_count < 3:
        score -= 3
    if not hunter_emails:
        score -= 2

    return {"score": max(0, score), "issues": issues, "titled_count": titled_count}


def _score_company(data) -> dict:
    """Score quality of company profile data."""
    company = data.get("company", {})
    issues = []
    if not _call_succeeded(company):
        issues.append("Company profile API failed")
        return {"score": 0, "issues": issues}

    org = company.get("data", {}).get("organization", {})
    if not org.get("name"):
        issues.append("No company name in profile")
    if not org.get("short_description") and not org.get("description"):
        issues.append("No company description")
    if not org.get("estimated_num_employees"):
        issues.append("No employee count")

    score = 10 - len(issues) * 2
    return {"score": max(0, score), "issues": issues}


def _score_news(data) -> dict:
    """Score quality of news data."""
    news = data.get("news", {})
    issues = []
    if not _call_succeeded(news):
        issues.append("News search failed")
        return {"score": 0, "issues": issues}

    results = news.get("data", {}).get("results", [])
    if not results:
        issues.append("No news results found")
        return {"score": 2, "issues": issues}

    if len(results) < 3:
        issues.append(f"Only {len(results)} news items (sparse)")

    score = min(10, len(results) * 2)
    return {"score": score, "issues": issues}


def _score_tech(data) -> dict:
    """Score quality of tech stack data."""
    tech = data.get("tech", {})
    if not _call_succeeded(tech):
        return {"score": 0, "issues": ["BuiltWith lookup failed"]}
    return {"score": 8, "issues": []}


async def _autonomous_enrich(locus, data, apis, company, domain, url, context, costs,
                             tier="base"):
    """Evaluate data quality and autonomously spend to fill gaps.

    Higher tiers get bigger enrichment budgets — Elite agent tries harder.

    Returns a list of enrichment actions taken:
    [{"action": "...", "reason": "...", "result": "...", "cost": 0.02}, ...]
    """
    enrichment_log = []
    budget_remaining = ENRICHMENT_BUDGET.get(tier, 0.10)

    # Score every data category
    scores = {
        "people":  _score_people(data),
        "company": _score_company(data),
        "news":    _score_news(data),
        "tech":    _score_tech(data),
    }

    log.info("Data quality scores: %s",
             {k: v["score"] for k, v in scores.items()})

    # ── DECISION 1: People data weak → try Hunter if not already called ──
    people_score = scores["people"]
    if people_score["score"] < 6 and "hunter" not in apis and domain:
        cost = COSTS["hunter"]
        if cost <= budget_remaining:
            log.info("Agent decision: people data weak (%s), calling Hunter",
                     "; ".join(people_score["issues"]))
            result = await _safe(locus.hunter_domain_search(domain))
            if _call_succeeded(result):
                data["people_combined"]["hunter"] = result
                costs["enrich_hunter"] = cost
                budget_remaining -= cost
                emails = result.get("data", {}).get("emails", [])
                enrichment_log.append({
                    "action": "Called Hunter email search",
                    "reason": "; ".join(people_score["issues"]),
                    "result": f"Found {len(emails)} email contacts",
                    "cost": cost,
                })
            else:
                enrichment_log.append({
                    "action": "Called Hunter email search",
                    "reason": "; ".join(people_score["issues"]),
                    "result": "API call failed — no additional data",
                    "cost": 0,
                })

    # ── DECISION 2: People still weak → try Apollo people if not called ──
    if people_score["score"] < 5 and "apollo_people" not in apis and domain:
        cost = COSTS["apollo_people"]
        if cost <= budget_remaining:
            log.info("Agent decision: people still weak, calling Apollo People")
            result = await _safe(locus.apollo_people_search(domain))
            if _call_succeeded(result):
                data["people_combined"]["apollo"] = result
                costs["enrich_apollo_people"] = cost
                budget_remaining -= cost
                people = (result.get("data", {}).get("people", [])
                          or result.get("data", {}).get("contacts", []))
                enrichment_log.append({
                    "action": "Called Apollo People search",
                    "reason": "People data critically weak after initial sweep",
                    "result": f"Found {len(people)} people profiles",
                    "cost": cost,
                })

    # ── DECISION 3: News data empty → broaden search query ──
    news_score = scores["news"]
    if news_score["score"] < 4:
        cost = COSTS["tavily"]
        if cost <= budget_remaining:
            log.info("Agent decision: news data weak, running broader search")
            result = await _safe(locus.tavily_search(
                f'"{company}" announcement OR partnership OR expansion 2025 2026',
                max_results=5, topic="news",
            ))
            if _call_succeeded(result):
                new_results = result.get("data", {}).get("results", [])
                if new_results:
                    # Merge with existing news
                    existing = data["news"].get("data", {}).get("results", []) if _call_succeeded(data["news"]) else []
                    seen_urls = {r.get("url") for r in existing}
                    added = [r for r in new_results if r.get("url") not in seen_urls]
                    if added:
                        if not _call_succeeded(data["news"]):
                            data["news"] = result
                        else:
                            data["news"]["data"]["results"].extend(added)
                        costs["enrich_tavily_news"] = cost
                        budget_remaining -= cost
                        enrichment_log.append({
                            "action": "Broadened news search",
                            "reason": "; ".join(news_score["issues"]),
                            "result": f"Found {len(added)} additional news items",
                            "cost": cost,
                        })

    # ── DECISION 4: No tech stack → try BuiltWith if not called ──
    tech_score = scores["tech"]
    if tech_score["score"] < 3 and "builtwith" not in apis and domain:
        cost = COSTS["builtwith"]
        if cost <= budget_remaining:
            log.info("Agent decision: no tech data, calling BuiltWith")
            result = await _safe(locus.builtwith_lookup(domain))
            if _call_succeeded(result):
                data["tech"] = result
                costs["enrich_builtwith"] = cost
                budget_remaining -= cost
                enrichment_log.append({
                    "action": "Called BuiltWith tech lookup",
                    "reason": "; ".join(tech_score["issues"]),
                    "result": "Tech stack data acquired",
                    "cost": cost,
                })

    # ── DECISION 5: Company profile weak → try website scrape for context ──
    company_score = scores["company"]
    if company_score["score"] < 5 and "firecrawl_home" not in apis and url:
        cost = COSTS["firecrawl"]
        if cost <= budget_remaining:
            log.info("Agent decision: company profile weak, scraping homepage")
            result = await _safe(locus.firecrawl_scrape(url))
            if _call_succeeded(result):
                data["website"] = result
                costs["enrich_firecrawl_home"] = cost
                budget_remaining -= cost
                enrichment_log.append({
                    "action": "Scraped company homepage",
                    "reason": "; ".join(company_score["issues"]),
                    "result": "Homepage content acquired for context",
                    "cost": cost,
                })

    # ── ELITE-ONLY: Extra enrichment passes ──
    if tier == "elite":
        # Re-score people after earlier enrichment attempts
        people_rescore = _score_people(data)
        if people_rescore["score"] < 8 and context and budget_remaining >= COSTS["tavily"]:
            cost = COSTS["tavily"]
            log.info("Agent decision [elite]: targeted people search using seller context")
            result = await _safe(locus.tavily_search(
                f'"{company}" {context[:80]} leadership team executive',
                max_results=5,
            ))
            if _call_succeeded(result):
                results_found = result.get("data", {}).get("results", [])
                if results_found:
                    costs["enrich_tavily_leaders"] = cost
                    budget_remaining -= cost
                    # Store as supplementary people intel
                    data["people_combined"]["tavily_leaders"] = result
                    enrichment_log.append({
                        "action": "Targeted leadership search (Elite)",
                        "reason": f"People still weak (score {people_rescore['score']}/10) — "
                                  "searching for leaders relevant to seller context",
                        "result": f"Found {len(results_found)} leadership references",
                        "cost": cost,
                    })

        # Elite: deeper competitive intel if not already strong
        if "tavily_competitors" not in apis and budget_remaining >= COSTS["tavily"]:
            cost = COSTS["tavily"]
            log.info("Agent decision [elite]: adding competitive intelligence")
            result = await _safe(locus.tavily_search(
                f'"{company}" vs competitors alternatives review comparison',
                max_results=5,
            ))
            if _call_succeeded(result):
                comp_results = result.get("data", {}).get("results", [])
                if comp_results:
                    data["competitor"] = result
                    costs["enrich_tavily_competitors"] = cost
                    budget_remaining -= cost
                    enrichment_log.append({
                        "action": "Added competitive intelligence (Elite)",
                        "reason": "Competitor data not in base tier — Elite agent adds it",
                        "result": f"Found {len(comp_results)} competitor insights",
                        "cost": cost,
                    })

    if enrichment_log:
        total_enrichment = sum(e["cost"] for e in enrichment_log)
        budget_limit = ENRICHMENT_BUDGET.get(tier, 0.10)
        log.info("Enrichment complete: %d actions, $%.4f spent (budget was $%.2f)",
                 len(enrichment_log), total_enrichment, budget_limit)

    return enrichment_log


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


async def _synthesise_full(locus, cfg, company, context, data, costs,
                           enrichment_log=None):
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
        enrichment_log=enrichment_log,
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
