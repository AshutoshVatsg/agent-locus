SYNTHESIS_SYSTEM = """\
You are an elite sales intelligence strategist. You do NOT write generic company \
summaries — you produce deeply cross-referenced, actionable briefings that make \
salespeople sound like they spent days researching a prospect.

Rules:
- FORMAT: Use bullet points, tables, and short punchy lines. NO long paragraphs. \
  Every insight should be scannable in 3 seconds. Bold the key takeaway in each bullet.
- CROSS-REFERENCE data sources. Connect hiring signals to pain points, tech stack \
  to displacement opportunities, news to timing angles. Every insight must link \
  multiple data points.
- Be SPECIFIC — cite names, dates, job titles, technologies, dollar amounts, \
  project names. No vague generalities.
- Write as if coaching a salesperson before a high-stakes call. Every bullet \
  should answer: "What do I SAY and WHY?"
- Structure output in clean Markdown with EXACTLY the section headings specified.
- Each section must start with its exact heading (e.g. "## 1. Company Snapshot").
- RECENCY FILTER: For news and signals, prioritise the last 6 months. Ignore \
  anything older than 12 months unless it is a major strategic shift. Always \
  include dates so the reader knows how fresh the intel is.
- If a data source returned an error or empty result, note it briefly and work \
  with what you have.
- NEVER fabricate data. Only use what is provided below.
- For people/decision-maker data: REJECT entries missing full names or clear \
  job titles. Do NOT include someone just because they have an email. \
  Quality over quantity — 3 validated decision-makers beat 10 unknowns.
- When referencing where you found something, use parenthetical citations like \
  (Apollo), (BuiltWith), (Careers Page), (News), (Hiring Signals)."""


# ═══════════════════════════════════════════════════════════════════
#  TIER TEMPLATES (full report synthesis)
# ═══════════════════════════════════════════════════════════════════

SYNTHESIS_USER_BASE = """\
Create a sales pitch-prep briefing for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Technology Stack (BuiltWith)
{tech_data}

### Website Content (Homepage Scrape)
{website_data}

### Recent News & Signals (Tavily)
{news_data}

{enrichment_block}

---
## OUTPUT — use exactly these sections. Use bullet points, NOT paragraphs.

## 1. Company Snapshot
Bullet points only:
- **What they do:** one line
- **HQ / Size / Funding:** one line
- **Key metrics:** revenue, headcount, growth signals
- **Strategic focus:** what they care about right now

## 2. Tech Stack & Opportunities
Table format:

| Technology | Category | Opportunity for Seller |
|-----------|----------|----------------------|

For each relevant tech: **Integration** / **Displace** / **Gap to fill** — one line why.

## 3. Timing Signals
Only include signals from the **last 6 months**. For each:
- **Signal:** what happened (with date)
- **Why it matters:** one line connecting it to seller's context
- **Pitch angle:** what to say about it

## 4. Why You Might Lose This Deal
Be brutally honest. Bullet points:
- **Competitor risk:** Do they already use a competing product? (check tech stack)
- **Build vs buy:** Could their engineering team build this internally? \
  (check hiring signals, team size)
- **Budget/timing risk:** Any signs of cost-cutting, layoffs, or freezes?
- **Champion gap:** Do you have a clear path to a decision-maker?

For each risk, add a one-line mitigation strategy.

## 5. Recommended Talking Points
Bullet format:
- **3 opening hooks** — each references a specific, dated company event
- **3 pain points to probe** — tied to tech stack gaps or news signals
- **Recommended next steps** — who to contact, what channel, what to say

## 6. Critical Deep Insights
3-5 bullet points that connect the dots across ALL data. Each insight must:
- Link 2+ data sources (e.g. tech stack + news + hiring)
- Be directly actionable for the seller's specific product
- Answer: "What does this mean for MY deal, specifically?"

Format: **Insight:** [cross-referenced finding] → **Action:** [what to do]"""


SYNTHESIS_USER_PRO = """\
Create a cross-referenced sales briefing for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Key People & Contacts (Apollo + Hunter)
{people_data}

### Technology Stack (BuiltWith)
{tech_data}

### Website Content (Homepage Scrape)
{website_data}

### Careers Page (Job Postings Scrape)
{careers_data}

### Recent News & Signals (Tavily)
{news_data}

### Hiring Signals (Tavily)
{hiring_data}

{enrichment_block}

---
## OUTPUT — use exactly these sections. Use bullet points, NOT paragraphs.

## 1. Company Snapshot
Bullet points only:
- **What they do:** one line
- **HQ / Size / Funding:** one line
- **Key metrics:** revenue, headcount, growth signals
- **Strategic focus:** what they care about right now
- **Recent momentum:** latest funding, product launch, or leadership change (with date)

## 2. Hiring Pain Detector
For each role cluster being hired, use this format:
- **Role:** [exact job title from posting]
- **Problem it reveals:** one line on what business pain this hiring signals
- **Your angle:** how the seller's product directly addresses this
- **Talk track:** one ready-to-use sentence referencing the posting

Example:
> - **Role:** 3x Senior Platform Engineers — "migrate legacy services to K8s" (Careers Page)
> - **Problem:** Infrastructure modernisation pain, legacy tech debt
> - **Your angle:** They have budget allocated for exactly this
> - **Talk track:** "I noticed you're scaling your platform team — we help companies \
cut that migration timeline in half."

If no careers data is available, infer hiring priorities from news and \
company growth signals.

## 3. Decision-Maker Map

STEP 1 — FILTER: From the raw people data, ONLY keep people who have:
- A full name (first AND last)
- A clear senior job title (CEO, CTO, VP, Head, Director, Chief, SVP, \
  EVP, President, Founder, Managing Director, or similar)
- OR are clearly part of a team relevant to the seller's context \
  (e.g. engineering, security, product, sales leadership)
REJECT anyone with: missing name, missing/vague title, generic entries, \
or low-confidence data.

STEP 2 — VALIDATE & RANK: Given the seller's context, determine which \
roles are MOST relevant for this pitch and rank by decision-making authority.

STEP 3 — OUTPUT: Markdown table — Name | Title | Tenure | Pitch Relevance.
Select the top 3-5 VALIDATED people. For each person:
- Why they matter for THIS specific pitch (be specific, not generic)
- Cross-reference their role with hiring signals and tech stack
- Flag anyone who joined recently (< 6 months) — new leaders re-evaluate tooling
- One personalised opener line for this person

STEP 4 — FALLBACK: If NO strong candidates exist in the data, output:
"⚠️ No high-confidence decision-makers identified from available data."
Then list 3-4 recommended target ROLES (e.g. VP Engineering, Head of \
Security) with why THOSE roles matter for the seller's context.

## 4. Tech Stack Displacement Map
Table format:

| Technology | Category | Status | Opportunity for Seller |
|-----------|----------|--------|----------------------|

Status = **Competitor** (displace) / **Integration** (connect) / **Gap** (greenfield). \
One line per row explaining the angle.

## 5. Timing Signals
Only include signals from the **last 6 months** with dates. For each:
- **Signal:** [what happened] — [date] (source)
- **Why now:** one line connecting to seller's product
- **Pitch angle:** what to say about it

## 6. Recent News & Signals
Only the **3-5 most recent and relevant** items (with dates). Skip old/generic news. \
For each:
- **[Date] — [Headline]** (source)
- **Sales opening:** one line on how to use this in outreach

## 7. Why You Might Lose This Deal
Be brutally honest. For each risk:
- **Risk:** [specific threat — e.g. "They already use Competitor X for this"]
- **Evidence:** [what data supports this — cite source]
- **Mitigation:** [one-line counter-strategy]

Cover these angles: competitor lock-in, build-vs-buy, budget/timing, champion gap, \
internal politics.

## 8. Recommended Battle Plan
Bullet format:
- **3 opening hooks** — each cites a SPECIFIC dated finding from above
- **3 pain points to probe** — tied to hiring signals or tech stack gaps
- **3 likely objections + responses** — grounded in data, not generic
- **Outreach sequence:** who to contact first → what channel → what to say

## 9. Critical Deep Insights
3-5 bullet points connecting the dots across ALL data sources. Each insight must:
- Link 2+ sources (e.g. hiring + tech stack + news)
- Be specific to the seller's product
- End with a concrete action

Format: **Insight:** [cross-referenced finding] → **Action:** [what to do about it]"""


SYNTHESIS_USER_ELITE = """\
Create a comprehensive, cross-referenced sales intelligence briefing \
for **{company}**.

{context_block}

---
## RAW INTELLIGENCE

### Company Profile (Apollo)
{company_data}

### Key People & Contacts (Apollo + Hunter)
{people_data}

### Technology Stack (BuiltWith)
{tech_data}

### Website Content (Homepage Scrape)
{website_data}

### Careers Page (Job Postings Scrape)
{careers_data}

### Blog & Press Releases (Blog Scrape)
{blog_data}

### Recent News & Signals (Tavily — 10 results)
{news_data}

### Hiring Market Signals (Tavily)
{hiring_data}

### Competitor Intelligence (Tavily)
{competitor_data}

{enrichment_block}

---
## OUTPUT — use exactly these sections. Use bullet points, NOT paragraphs.

## 1. Company Snapshot
Bullet points only:
- **What they do:** one line
- **HQ / Size / Funding:** one line
- **Key metrics:** revenue, headcount, growth rate
- **Strategic focus:** what they care about right now (inferred from all sources)
- **Recent momentum:** latest 2-3 events with dates

## 2. Hiring Pain Detector
For each role cluster being hired:
- **Role:** [exact job title from posting]
- **Problem it reveals:** what business pain this signals
- **Your angle:** how the seller's product directly solves this
- **Talk track:** one ready-to-use sentence referencing the posting

If scaling a team (e.g. "5 DevOps engineers"), flag: \
"**Budget signal** — they're actively investing here."

## 3. Company Initiatives & Projects
For each NAMED initiative/project found in blog/press/website:
- **Initiative:** [name] — announced [date] (source)
- **What it is:** one line
- **Connection to seller:** how your product plugs into this
- **Name-drop:** "I saw you're working on [X]..."

## 4. Decision-Maker Intelligence

STEP 1 — FILTER: From the raw people data, ONLY keep people who have:
- A full name (first AND last)
- A clear senior job title (CEO, CTO, VP, Head, Director, Chief, SVP, \
  EVP, President, Founder, Managing Director, or team lead in a \
  relevant department)
REJECT anyone with: missing name, missing/vague title, generic entries, \
low-confidence emails, or no clear relevance to the seller's context. \
Do NOT guess roles or fabricate profiles.

STEP 2 — VALIDATE & RANK: Given the seller's context, determine which \
people are MOST relevant. Prioritise decision-makers with budget \
authority in the relevant area.

STEP 3 — OUTPUT: Markdown table — Name | Title | Tenure | Email | Pitch Relevance.
Select the top 5-8 VALIDATED people. For each:
- Why they matter for THIS pitch (specific, not generic)
- If tenure < 6 months: flag as "new leader — likely re-evaluating tools"
- Cross-reference with hiring signals (e.g. "Owns the platform team \
  that's hiring 5 engineers — has budget authority")
- One personalised opener for this specific person

STEP 4 — FALLBACK: If the raw data lacks strong candidates (missing \
titles, names only, low confidence), DO NOT pad the table with weak entries. \
Instead output:
"⚠️ No high-confidence decision-makers identified from available data."
Then list 3-4 recommended target ROLES with why they matter for this pitch \
and suggest LinkedIn/email outreach strategies for those roles.

## 5. Tech Stack Displacement Map
Table format:

| Category | Current Tool | Status | Opportunity for Seller |
|----------|-------------|--------|----------------------|

Status = **Displace** / **Integrate** / **Gap**. One line per row. \
Only include technologies relevant to the seller's product.

## 6. Competitive Landscape & Displacement
Bullet format:
- **Top 3-5 competitors** — one line each on how the target positions against them
- **Competitor products IN USE** (cross-ref BuiltWith):
  - **[Product]** → Displacement strategy: [specific angle]
- **Comparison table:**

| Competitor | Their Strength | Their Weakness | Your Angle |
|-----------|---------------|----------------|------------|

## 7. Timing Signal Triangulation
Only signals from the **last 6 months** with dates. Score overall urgency (1-10):
- **[Signal]** — [date] (source + source) → **Pitch angle:** [one line]

End with: **Bottom Line — Why This Week:** 2-3 bullet points synthesising \
the strongest timing signals into a "contact them NOW" case.

## 8. Why You Might Lose This Deal
Be brutally honest. For each risk:
- **Risk:** [specific threat]
- **Evidence:** [data that supports this — cite source]
- **Mitigation:** [counter-strategy]

Must cover:
- **Competitor lock-in** — do they already use a competing product?
- **Build vs buy** — could their team build this? (check eng headcount, hiring)
- **Budget/timing** — signs of cost-cutting, layoffs, or freezes?
- **Champion gap** — is there a clear path to a decision-maker?
- **Internal politics** — any reorgs, leadership changes that could stall deals?

## 9. Recommended Battle Plan
Bullet format:
- **5 opening hooks** — each cites a specific dated finding with source
- **5 pain points to probe** — mapped to hiring signals, tech gaps, or initiatives
- **5 likely objections + responses** — tied to competitive landscape data
- **Outreach sequence:** who to email first → subject line → what to reference
- **Follow-up strategy:** what to send after the first call

## 10. Critical Deep Insights
5-7 bullet points that connect the dots across ALL data sources. \
Each insight MUST:
- Link 2+ sources (e.g. hiring + tech stack + competitor intel + news)
- Be directly tied to the seller's specific product
- Answer: "What does this mean for MY deal?"
- End with a concrete next step

Format: **Insight:** [cross-referenced finding] → **Action:** [what to do]

End with: **Deal Probability:** [High/Medium/Low] — one line justification \
based on the evidence above."""


TIER_TEMPLATES = {
    "base":  SYNTHESIS_USER_BASE,
    "pro":   SYNTHESIS_USER_PRO,
    "elite": SYNTHESIS_USER_ELITE,
}


# ═══════════════════════════════════════════════════════════════════
#  ADD-ON PROMPTS (single section synthesis, appended to existing report)
# ═══════════════════════════════════════════════════════════════════

ADDON_SYSTEM = """\
You are an elite sales intelligence strategist. You are generating ONE \
focused section to add to an existing sales briefing. Cross-reference the \
new data with the base context provided.

Rules:
- Be SPECIFIC — cite names, dates, job titles, technologies, amounts.
- Write for a salesperson about to walk into a call.
- Output ONLY the requested section in Markdown (one ## heading + content).
- NEVER fabricate data. Use parenthetical citations like (Careers Page), (Apollo)."""

ADDON_PROMPTS = {
    "hiring_pain": """\
Generate a single section for **{company}**.

{context_block}

### Base Context (already in report)
Company: {company_data_summary}
Tech Stack: {tech_data_summary}

### NEW DATA — Careers Page (Scraped)
{careers_data}

### NEW DATA — Hiring Market Signals
{hiring_data}

---
## Hiring Pain Detector

Analyse the careers page and hiring signals. For each role cluster:
- The EXACT job titles and key phrases from postings
- What PROBLEM the company is solving by hiring for this
- How the seller's product DIRECTLY addresses that problem
- A ready-to-use talk track referencing the specific posting

If scaling a team (multiple hires for same role), flag as a budget signal.""",

    "decision_makers": """\
Generate a single section for **{company}**.

{context_block}

### Base Context (already in report)
Company: {company_data_summary}
Tech Stack: {tech_data_summary}

### NEW DATA — Key People (Apollo)
{people_data}

### NEW DATA — Email Contacts (Hunter)
{hunter_data}

---
## Decision-Maker Intelligence

IMPORTANT RULES:
- Do NOT guess names or roles. Do NOT include incomplete profiles.
- ONLY include people who have a full name AND a clear job title.
- REJECT entries with missing names, missing titles, generic roles, \
  or low-confidence emails.

STEP 1 — FILTER: From the raw data, ONLY keep people with:
- Full name (first AND last)
- Senior title: CEO, CTO, VP, Head, Director, Chief, SVP, EVP, \
  President, Founder, Managing Director, or team lead in a relevant dept
- Clear relevance to the seller's context

STEP 2 — ROLE MAPPING: Given the seller's context, determine which \
roles are MOST relevant for this pitch and why they would care.

STEP 3 — OUTPUT: Markdown table — Name | Title | Tenure | Email | Pitch Relevance.
Select top 3-5 VALIDATED people. For each:
- Why they matter for THIS specific pitch (specific, not generic)
- If tenure < 6 months: "new leader — likely re-evaluating tools"
- One personalised opener for this person

STEP 4 — FALLBACK: If NO strong candidates exist in the data, output:
"⚠️ No high-confidence decision-makers identified from available data."
Then list 3-4 recommended target ROLES (e.g. VP Engineering, Head of \
Security) with why those roles matter for the seller's context and \
how to find them (LinkedIn search tips).""",

    "initiatives": """\
Generate a single section for **{company}**.

{context_block}

### Base Context (already in report)
Company: {company_data_summary}

### NEW DATA — Blog & Press Releases (Scraped)
{blog_data}

---
## Company Initiatives & Projects

Extract NAMED initiatives, projects, or strategic priorities. For each:
- What it is and when announced
- How the seller's product connects to it
- A name-drop suggestion (e.g. "I saw you're working on Project Atlas...")""",

    "competitor_intel": """\
Generate a single section for **{company}**.

{context_block}

### Base Context (already in report)
Company: {company_data_summary}
Tech Stack: {tech_data_summary}

### NEW DATA — Competitor Intelligence
{competitor_data}

---
## Competitive Landscape & Displacement

- Top 3-5 competitors and positioning
- Cross-reference with tech stack: if target USES a competitor, give displacement strategy
- Comparison table: Competitor | Strength | Weakness | Your Angle""",
}


# ═══════════════════════════════════════════════════════════════════
#  BUILDERS
# ═══════════════════════════════════════════════════════════════════

def build_synthesis_prompt(company, context, company_data, people_data,
                           tech_data, website_data, careers_data, blog_data,
                           news_data, hiring_data, competitor_data,
                           tier="base", enrichment_log=None):
    ctx = (
        f"**Seller's context:** {context}\n"
        "Tailor EVERY section to this seller's specific situation. "
        "Every recommendation must explain how it helps THIS seller "
        "close THIS deal."
    ) if context else ""

    enrichment_block = ""
    if enrichment_log:
        lines = ["### Agent Enrichment Actions",
                 "The agent autonomously spent USDC to improve this report:"]
        for e in enrichment_log:
            lines.append(f"- **{e['action']}** (${e['cost']:.3f}) — "
                         f"Reason: {e['reason']} → Result: {e['result']}")
        lines.append("")
        lines.append("Reference these enrichment actions in your report where "
                     "the enriched data improved a section.")
        enrichment_block = "\n".join(lines)

    template = TIER_TEMPLATES.get(tier, SYNTHESIS_USER_BASE)

    return template.format(
        company=company,
        context_block=ctx,
        enrichment_block=enrichment_block,
        company_data=_trunc(str(company_data), 3000),
        people_data=_trunc(str(people_data), 3000),
        tech_data=_trunc(str(tech_data), 2500),
        website_data=_trunc(str(website_data), 3000),
        careers_data=_trunc(str(careers_data), 3000),
        blog_data=_trunc(str(blog_data), 3000),
        news_data=_trunc(str(news_data), 2500),
        hiring_data=_trunc(str(hiring_data), 2000),
        competitor_data=_trunc(str(competitor_data or {}), 2000),
    )


def build_addon_prompt(addon_key, company, context, order_data, new_data):
    """Build a focused prompt for a single add-on section.

    order_data: dict of existing order fields (company_data, tech_data, etc.)
    new_data:   dict of freshly-fetched data for this add-on
    """
    ctx = (
        f"**Seller's context:** {context}\n"
        "Tailor this section to help THIS seller close THIS deal."
    ) if context else ""

    template = ADDON_PROMPTS[addon_key]

    # summaries of base data for cross-referencing (keep small)
    company_summary = _trunc(str(order_data.get("company_data", "{}")), 1500)
    tech_summary = _trunc(str(order_data.get("tech_data", "{}")), 1000)

    return template.format(
        company=company,
        context_block=ctx,
        company_data_summary=company_summary,
        tech_data_summary=tech_summary,
        # new data fields — each addon uses different ones
        careers_data=_trunc(str(new_data.get("careers_data", "{}")), 3000),
        hiring_data=_trunc(str(new_data.get("hiring_data", "{}")), 2000),
        people_data=_trunc(str(new_data.get("people_data", "{}")), 3000),
        hunter_data=_trunc(str(new_data.get("hunter_data", "{}")), 2000),
        blog_data=_trunc(str(new_data.get("blog_data", "{}")), 3000),
        competitor_data=_trunc(str(new_data.get("competitor_data", "{}")), 2000),
    )


def _trunc(text, n):
    return text if len(text) <= n else text[:n] + "\n…[truncated]"
