SYNTHESIS_SYSTEM = """\
You are a senior sales intelligence analyst. You produce executive-quality \
briefing documents that help salespeople prepare for calls and close deals.

Rules:
- Be specific and data-driven — cite numbers, dates, names.
- Structure output in clean Markdown with clear section headings exactly as specified.
- Each section must start with its exact heading (e.g. "## 1. Company Snapshot").
- If a data source returned an error or empty result, say so briefly and move on.
- NEVER fabricate data. Only use what is provided below."""

SYNTHESIS_USER_STARTER = """\
Create a sales briefing for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Recent News & Signals (Tavily)
{news_data}

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
One paragraph: what they do, HQ, size, funding stage, key metrics.

## 2. Recent Signals
News, funding rounds, product launches, leadership changes — anything that opens a conversation.

## 3. Recommended Talking Points
Personalised to the seller's context:
- 3 opening hooks
- 3 pain points to probe
- Recommended next steps"""

SYNTHESIS_USER_PRO = """\
Create a sales briefing for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Key People & Contacts (Apollo + Hunter)
{people_data}

### Technology Stack (BuiltWith)
{tech_data}

### Website Content (Firecrawl)
{website_data}

### Recent News & Signals (Tavily)
{news_data}

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
One paragraph: what they do, HQ, size, funding stage, key metrics.

## 2. Key Decision Makers
Markdown table — Name | Title | Email | Why They Matter. Top 5-8 people.

## 3. Technology Stack
Bullet list of notable technologies. Flag anything relevant to the seller's context.

## 4. Product & Market Positioning
What they sell, to whom, pricing model, market position.

## 5. Recent Signals
News, funding rounds, product launches, leadership changes — anything that opens a conversation.

## 6. Competitive Landscape
Top 2-3 competitors and how this company differentiates.

## 7. Recommended Talking Points
Personalised to the seller's context:
- 3 opening hooks
- 3 pain points to probe
- 3 likely objections + suggested responses
- Recommended next steps"""

SYNTHESIS_USER_ELITE = """\
Create a comprehensive sales briefing for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Key People & Contacts (Apollo + Hunter)
{people_data}

### Technology Stack (BuiltWith)
{tech_data}

### Website Content (Firecrawl)
{website_data}

### Recent News & Signals (Tavily — 10 results)
{news_data}

### Competitor Research (Tavily)
{competitor_data}

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
Two paragraphs: what they do, HQ, size, funding stage, key metrics, strategic priorities.

## 2. Key Decision Makers
Markdown table — Name | Title | Email | LinkedIn Signals | Why They Matter. Top 8-10 people.

## 3. Technology Stack
Bullet list of notable technologies, categorised (infra, analytics, marketing, payments). Flag anything relevant.

## 4. Product & Market Positioning
What they sell, to whom, pricing model, market position, unique differentiators.

## 5. Recent Signals
Detailed analysis of news, funding, product launches, leadership changes, hiring signals.

## 6. Competitive Landscape
Top 3-5 competitors with comparison table: Company | Strength | Weakness | How to position against them.

## 7. Account Intelligence Summary
Key risks, expansion signals, budget indicators, timeline triggers.

## 8. Recommended Talking Points
Personalised and deeply tailored:
- 5 opening hooks (with specific references to their recent news/signals)
- 5 pain points to probe
- 5 likely objections + suggested responses
- Strategic next steps + follow-up sequence"""

TIER_TEMPLATES = {
    "starter": SYNTHESIS_USER_STARTER,
    "pro":     SYNTHESIS_USER_PRO,
    "elite":   SYNTHESIS_USER_ELITE,
}


def build_synthesis_prompt(company, context, company_data, people_data,
                           tech_data, website_data, news_data,
                           competitor_data=None, tier="pro"):
    ctx = (f"**Seller's context:** {context}\n"
           "Personalise talking points and analysis for this seller.") if context else ""

    template = TIER_TEMPLATES.get(tier, SYNTHESIS_USER_PRO)

    # Python's str.format() silently ignores keys not used by the template,
    # so all tiers can share the same kwargs dict safely.
    return template.format(
        company=company,
        context_block=ctx,
        company_data=_trunc(str(company_data), 3000),
        people_data=_trunc(str(people_data), 3000),
        tech_data=_trunc(str(tech_data), 2000),
        website_data=_trunc(str(website_data), 3000),
        news_data=_trunc(str(news_data), 2000),
        competitor_data=_trunc(str(competitor_data or {}), 2000),
    )


def _trunc(text, n):
    return text if len(text) <= n else text[:n] + "\n…[truncated]"
