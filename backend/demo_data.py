"""Demo-mode sample data and report generation helpers."""

from __future__ import annotations

from typing import Any

DEMO_PRESETS = [
    {
        "company_name": "Stripe",
        "company_domain": "stripe.com",
        "context": "I sell a developer observability platform for engineering leaders preparing for major reliability improvements.",
        "summary": "Payments infrastructure at global scale with strong platform, developer tooling, and enterprise expansion signals.",
    },
    {
        "company_name": "Notion",
        "company_domain": "notion.so",
        "context": "I sell workflow analytics and knowledge operations tooling for product and operations teams.",
        "summary": "Fast-growing collaboration platform with strong product velocity, cross-functional adoption, and AI packaging opportunities.",
    },
    {
        "company_name": "HubSpot",
        "company_domain": "hubspot.com",
        "context": "I sell AI-assisted revenue operations tooling for GTM and customer success leadership.",
        "summary": "Scaled SaaS platform with broad GTM surface area, large installed base, and clear competitive messaging needs.",
    },
]


def get_demo_presets() -> list[dict[str, str]]:
    return [
        {
            "company_name": preset["company_name"],
            "company_domain": preset["company_domain"],
            "context": preset["context"],
            "summary": preset["summary"],
        }
        for preset in DEMO_PRESETS
    ]


def find_demo_preset(company_name: str, domain: str = "") -> dict[str, str]:
    company_name = (company_name or "").strip().lower()
    domain = (domain or "").strip().lower()

    for preset in DEMO_PRESETS:
        if company_name and preset["company_name"].lower() == company_name:
            return preset
        if domain and preset["company_domain"].lower() == domain:
            return preset

    fallback = DEMO_PRESETS[0].copy()
    if company_name:
        fallback["company_name"] = company_name.title()
    if domain:
        fallback["company_domain"] = domain
    return fallback


def build_demo_raw_data(preset: dict[str, str], tier: str) -> dict[str, Any]:
    company = preset["company_name"]
    domain = preset["company_domain"]

    base = {
        "company_data": {
            "success": True,
            "data": {
                "organization": {
                    "name": company,
                    "website_url": f"https://{domain}",
                    "estimated_num_employees": 3500 if company == "Stripe" else 1800,
                    "short_description": preset["summary"],
                    "industry": "Software",
                }
            },
        },
        "tech_data": {
            "success": True,
            "data": {
                "groups": [
                    {"name": "AWS", "category": "Cloud Infrastructure"},
                    {"name": "React", "category": "Frontend Framework"},
                    {"name": "Segment", "category": "Analytics"},
                    {"name": "Snowflake", "category": "Data Platform"},
                ]
            },
        },
        "website_data": {
            "success": True,
            "data": {
                "markdown": f"{company} positions itself around speed, trust, platform reliability, and enterprise-grade extensibility."
            },
        },
        "news_data": {
            "success": True,
            "data": {
                "results": [
                    {"title": f"{company} expands enterprise capabilities", "published_date": "2026-03-10"},
                    {"title": f"{company} highlights AI roadmap", "published_date": "2026-02-18"},
                    {"title": f"{company} launches customer-focused workflow improvements", "published_date": "2026-01-22"},
                ]
            },
        },
        "people_data": {
            "apollo": {
                "success": True,
                "data": {
                    "people": [
                        {"first_name": "Alex", "last_name": "Morgan", "title": "VP Engineering"},
                        {"first_name": "Jordan", "last_name": "Lee", "title": "Head of Platform"},
                        {"first_name": "Sam", "last_name": "Patel", "title": "Director of Infrastructure"},
                    ]
                },
            },
            "hunter": {
                "success": True,
                "data": {
                    "emails": [
                        {"value": f"alex.morgan@{domain}"},
                        {"value": f"jordan.lee@{domain}"},
                    ]
                },
            },
        },
        "careers_data": {
            "success": True,
            "data": {
                "markdown": "Hiring for platform engineering, data infrastructure, security, and product analytics roles."
            },
        },
        "blog_data": {
            "success": True,
            "data": {
                "markdown": "Recent posts emphasize platform scale, AI-assisted workflows, and enterprise trust."
            },
        },
        "hiring_data": {
            "success": True,
            "data": {
                "results": [
                    {"title": "Senior Platform Engineer", "snippet": "Improve service reliability and deployment workflows"},
                    {"title": "Staff Data Engineer", "snippet": "Own analytics infrastructure and operational visibility"},
                ]
            },
        },
        "competitor_data": {
            "success": True,
            "data": {
                "results": [
                    {"title": "Competitive review signals incumbent tooling overlap"},
                    {"title": "Market narratives suggest migration pressure on legacy workflows"},
                ]
            },
        },
    }

    if tier == "base":
        base["people_data"] = {}
        base["careers_data"] = {}
        base["blog_data"] = {}
        base["hiring_data"] = {}
        base["competitor_data"] = {}

    return base


def build_demo_report(preset: dict[str, str], tier: str, context: str) -> str:
    company = preset["company_name"]
    domain = preset["company_domain"]
    seller_context = context.strip() or preset["context"]

    base_sections = f"""## 1. Company Snapshot
- **What they do:** {company} is positioned as a platform business with strong enterprise trust and scale requirements.
- **Why it matters:** Their public messaging centers on speed, reliability, and extensibility, which maps well to platform-facing tooling.
- **Domain:** `{domain}`
- **Seller context:** {seller_context}

## 2. Tech Stack & Opportunities
| Technology | Category | Opportunity for Seller |
|-----------|----------|----------------------|
| AWS | Cloud Infrastructure | **Integration:** reliability and observability tooling can attach to a mature cloud stack. |
| React | Frontend Framework | **Integration:** front-end performance and product usage analytics are easy angles. |
| Segment | Analytics | **Displace or complement:** useful opening for better pipeline visibility and activation quality. |
| Snowflake | Data Platform | **Gap to fill:** strong indicator they care about data maturity and operational reporting. |

## 3. Timing Signals
- **Signal:** Enterprise capability expansion announced on March 10, 2026.
- **Why it matters:** Expansion often creates pressure on reliability, reporting, and internal tooling consistency.
- **Pitch angle:** Lead with reduced operational drag during scale-up periods.

- **Signal:** AI roadmap highlighted on February 18, 2026.
- **Why it matters:** New AI initiatives usually surface instrumentation, governance, and workflow coordination needs.
- **Pitch angle:** Position your product as acceleration infrastructure, not just another tool.

## 4. Why You Might Lose This Deal
- **Competitor risk:** They likely already have mature internal systems. **Mitigation:** pitch time-to-value and lower implementation friction.
- **Build vs buy:** Strong engineering culture may push them to build internally. **Mitigation:** focus on speed, coverage, and reduced maintenance burden.
- **Budget/timing risk:** Priorities may favor customer-facing launches over internal tooling. **Mitigation:** tie value directly to launch velocity and reliability.
- **Champion gap:** If you miss the right technical owner, this stalls. **Mitigation:** start with engineering or platform leadership.

## 5. Recommended Talking Points
- **Opening hook:** "I noticed {company} is leaning into enterprise expansion and AI packaging at the same time."
- **Pain point to probe:** "Where is the current bottleneck when teams need trustworthy operational insight fast?"
- **Pain point to probe:** "How much manual coordination is still needed between platform, data, and product teams?"
- **Recommended next step:** target a platform or engineering leader with a short, evidence-based outreach note.

## 6. Critical Deep Insights
- **Insight:** Enterprise expansion plus AI packaging usually increases tooling sprawl. → **Action:** pitch consolidation, observability, and execution confidence.
- **Insight:** Their stack suggests data maturity but not necessarily smooth cross-team execution. → **Action:** sell operational clarity, not raw analytics.
- **Insight:** Reliability and roadmap velocity are likely both board-level concerns. → **Action:** tie your value to fewer delays and faster rollout confidence."""

    pro_sections = f"""

## 7. Hiring Pain Detector
- **Role:** Senior Platform Engineer.
- **Problem it reveals:** They are investing in service reliability and internal developer efficiency.
- **Your angle:** Your product reduces debugging cycles and gives leaders better operational visibility.
- **Talk track:** "I saw platform hiring tied to reliability improvements, which usually means your team is under pressure to move faster without breaking things."

- **Role:** Staff Data Engineer.
- **Problem it reveals:** Reporting quality and data operations remain active priorities.
- **Your angle:** Show how your product improves decision speed with less manual stitching.
- **Talk track:** "Teams scaling analytics infrastructure usually want fewer blind spots between product behavior and operational outcomes."

## 8. Decision-Maker Map
| Name | Title | Tenure | Pitch Relevance |
|------|-------|--------|-----------------|
| Alex Morgan | VP Engineering | 2.1 years | Senior technical sponsor for reliability, scale, and execution speed |
| Jordan Lee | Head of Platform | 1.4 years | Natural owner for infrastructure tooling and team efficiency |
| Sam Patel | Director of Infrastructure | 0.8 years | Likely operator for rollout, reliability, and implementation details |

- **Why they matter:** These roles sit closest to the pain created by platform scale, release confidence, and instrumentation gaps.
- **Personalized opener:** "I noticed hiring and roadmap signals pointing to infrastructure pressure. Curious how your team is handling visibility as priorities expand."

## 9. Tech Stack Displacement Map
| Technology | Category | Status | Opportunity for Seller |
|-----------|----------|--------|----------------------|
| AWS | Cloud Infrastructure | Integration | Anchor the conversation around scale and reliability. |
| Segment | Analytics | Competitor / Adjacent | Differentiate on speed-to-insight and operational actionability. |
| Snowflake | Data Platform | Integration | Strong opportunity to complement, not replace, existing systems. |

## 10. Recommended Battle Plan
- **Opening hook:** Reference the March 10 enterprise expansion signal and the February 18 AI roadmap update.
- **Pain point to probe:** Ask where platform teams still rely on manual correlation across tools.
- **Likely objection:** "We already have internal tooling." **Response:** emphasize reduced maintenance and faster time to dependable insight.
- **Outreach sequence:** VP Engineering -> Head of Platform -> Director of Infrastructure."""

    elite_sections = f"""

## 11. Company Initiatives
- **Initiative:** Scale enterprise readiness without slowing product teams.
- **Initiative:** Package AI capabilities in a way that stays trustworthy and measurable.
- **Initiative:** Improve cross-functional execution between engineering, data, and product.

## 12. Competitor Displacement
- **Risk:** Existing analytics and internal tooling may feel "good enough."
- **Displacement angle:** Reframe the category around execution confidence, not dashboards.
- **Timing angle:** New roadmap pressure makes "good enough" systems visibly brittle.

## 13. Strategic Outreach Sequence
- **Message 1:** Use the enterprise expansion signal to open a high-level problem statement.
- **Message 2:** Follow with a concrete operational pain tied to reliability or workflow visibility.
- **Message 3:** Offer a short working session framed around reducing coordination overhead and launch risk."""

    if tier == "base":
        return base_sections
    if tier == "pro":
        return base_sections + pro_sections
    return base_sections + pro_sections + elite_sections


def build_demo_addon_section(addon_key: str, preset: dict[str, str], context: str) -> str:
    company = preset["company_name"]
    seller_context = context.strip() or preset["context"]

    sections = {
        "hiring_pain": f"""## Hiring Pain Analysis
- **Signal:** {company} is hiring into platform and data-facing roles.
- **What it reveals:** Leadership is still investing in foundational systems and execution speed.
- **Why it matters for this pitch:** {seller_context}
- **Judge note:** Demo mode uses simulated hiring intelligence to show the post-purchase expansion flow.""",
        "decision_makers": f"""## Decision Maker Intel
| Name | Title | Why they matter |
|------|-------|-----------------|
| Alex Morgan | VP Engineering | High-authority sponsor for platform, reliability, and tooling budgets |
| Jordan Lee | Head of Platform | Ideal technical champion for implementation fit |
| Sam Patel | Director of Infrastructure | Practical owner for rollout concerns and success criteria |""",
        "initiatives": f"""## Company Initiatives
- **Initiative:** Improve enterprise trust and execution consistency.
- **Initiative:** Package AI capabilities without creating operational chaos.
- **Initiative:** Reduce friction between product velocity and infrastructure confidence.""",
        "competitor_intel": f"""## Competitor Displacement
- **Observed risk:** Existing tooling and internal workflows may anchor the status quo.
- **Displacement message:** Position your product around speed-to-confidence, not feature parity.
- **Best angle:** Tie the conversation to current scale pressure and organizational complexity.""",
    }
    return sections[addon_key]

