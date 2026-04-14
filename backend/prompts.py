SYNTHESIS_SYSTEM = """\
You are a senior sales intelligence analyst. You produce executive-quality \
briefing documents that help salespeople prepare for calls and close deals.

Rules:
- Be specific and data-driven — cite numbers, dates, names.
- Structure output in clean Markdown with clear headings.
- If a data source returned an error or empty result, say so briefly and move on.
- NEVER fabricate data. Only use what is provided below."""

SYNTHESIS_USER = """\
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

### 1. Company Snapshot
One paragraph: what they do, HQ, size, funding stage, key metrics.

### 2. Key Decision Makers
Markdown table — Name | Title | Email | Why They Matter.  Top 5-8 people.

### 3. Technology Stack
Bullet list of notable technologies. Flag anything relevant to the seller's context.

### 4. Product & Market Positioning
What they sell, to whom, pricing model, market position.

### 5. Recent Signals
News, funding rounds, product launches, leadership changes — anything that opens a conversation.

### 6. Competitive Landscape
Top 2-3 competitors and how this company differentiates.

### 7. Recommended Talking Points
Personalised to the seller's context:
- 3 opening hooks
- 3 pain points to probe
- 3 likely objections + suggested responses
- Recommended next steps"""


def build_synthesis_prompt(company, context, company_data, people_data,
                           tech_data, website_data, news_data):
    ctx = ""
    if context:
        ctx = (f"**Seller's context:** {context}\n"
               "Personalise talking points and analysis for this seller.")

    return SYNTHESIS_USER.format(
        company=company,
        context_block=ctx,
        company_data=_trunc(str(company_data), 3000),
        people_data=_trunc(str(people_data), 3000),
        tech_data=_trunc(str(tech_data), 2000),
        website_data=_trunc(str(website_data), 3000),
        news_data=_trunc(str(news_data), 2000),
    )


def _trunc(text, n):
    return text if len(text) <= n else text[:n] + "\n…[truncated]"
