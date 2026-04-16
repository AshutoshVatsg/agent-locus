SYNTHESIS_SYSTEM = """\
You are an elite sales intelligence strategist. You do NOT write generic company \
summaries — you produce deeply cross-referenced, actionable briefings that make \
salespeople sound like they spent days researching a prospect.

Rules:
- CROSS-REFERENCE data sources. Connect hiring signals to pain points, tech stack \
  to displacement opportunities, news to timing angles. Every insight must link \
  multiple data points.
- Be SPECIFIC — cite names, dates, job titles, technologies, dollar amounts, \
  project names. No vague generalities.
- Write as if coaching a salesperson before a high-stakes call. Every sentence \
  should answer: "What do I SAY and WHY?"
- Structure output in clean Markdown with EXACTLY the section headings specified.
- Each section must start with its exact heading (e.g. "## 1. Company Snapshot").
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

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
One paragraph: what they do, HQ, size, funding stage, key metrics.

## 2. Tech Stack & Opportunities
Bullet list of notable technologies they use (BuiltWith). For each one \
relevant to the seller's context, note whether it's a potential integration \
point, a competitor to displace, or a gap to fill.

## 3. Timing Signals
Why NOW is the right time to reach out. Cross-reference news (funding, \
launches, leadership changes) with any other signals. Each signal should \
end with a one-line pitch angle.

## 4. Recommended Talking Points
Personalised to the seller's context:
- 3 opening hooks that reference specific, recent company events
- 3 pain points to probe (tied to tech stack or news signals)
- Recommended next steps"""


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

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
One paragraph: what they do, HQ, size, funding stage, key metrics.

## 2. Hiring Pain Detector
Analyse the careers page scrape and hiring signals. Extract specific job \
titles and responsibilities being hired for. For each role cluster, explain:
- What PROBLEM the company is trying to solve by hiring for this
- How the seller's product/service DIRECTLY addresses that problem
- A suggested talk track referencing the specific job posting

Example format:
> "They're hiring 3 Senior Platform Engineers to 'migrate legacy services \
to Kubernetes' (Careers Page). This signals infrastructure modernisation \
pain. **Your pitch angle:** Lead with container orchestration — they have \
budget allocated for exactly this."

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
For each technology found via BuiltWith:
- Categorise it (infra, analytics, marketing, payments, security)
- Flag direct COMPETITORS to the seller's product → include displacement angle
- Flag INTEGRATION points → how the seller's tool connects
- Flag GAPS where they have no solution → greenfield opportunity

## 5. Timing Signals
Cross-reference ALL data sources to build a "Why Now" case:
- Funding events + headcount growth = budget available
- New leadership + hiring surge = re-evaluating tools
- Product launches + tech stack changes = active investment
Each signal must cite its source and end with a pitch angle.

## 6. Recent News & Signals
Key news, funding rounds, product launches, leadership changes. \
For each item, add a one-line note on how it creates a sales opening.

## 7. Recommended Battle Plan
Deeply personalised to the seller's context:
- 3 opening hooks (each must reference a SPECIFIC finding from above)
- 3 pain points to probe (tied to hiring signals or tech stack gaps)
- 3 likely objections + suggested responses
- Recommended outreach sequence (who to contact first, what to say)"""


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

---
## OUTPUT — use exactly these sections

## 1. Company Snapshot
Two paragraphs: what they do, HQ, size, funding stage, key metrics, \
strategic priorities inferred from all sources.

## 2. Hiring Pain Detector
Deep analysis of careers page + hiring market signals. For each role \
cluster being hired:
- The EXACT job titles and key phrases from the postings
- What business problem this hiring wave reveals
- How the seller's product directly solves it
- A ready-to-use talk track referencing the specific posting

If they're scaling a team (e.g. "5 DevOps engineers"), flag this as a \
budget signal — they're investing heavily in that area.

## 3. Company Initiatives & Projects
Extract NAMED initiatives, projects, or strategic priorities from the \
blog, press releases, and website. Examples: "Project Atlas", "AI-First \
Strategy", "Cloud Migration Initiative". For each:
- What it is and when it was announced
- How the seller's product connects to it
- A name-drop suggestion for the call (e.g. "I saw you're working on \
  Project Atlas...")

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
Categorised technology audit with competitive analysis:

| Category | Current Tool | Status | Opportunity |
|----------|-------------|--------|-------------|
| Infra | AWS ECS | Incumbent | Migration target if selling K8s |
| Analytics | Google Analytics | Gap | No product analytics tool |

For each entry relevant to the seller:
- Displacement angle (if they use a competitor)
- Integration story (if they use a complement)
- Greenfield pitch (if they have a gap)

## 6. Competitive Landscape & Displacement
From competitor intelligence:
- Top 3-5 competitors and how the target company positions against them
- If the target USES any competitor products (cross-ref with BuiltWith), \
  provide specific displacement strategy
- Customer reviews/sentiment about competitor products they might use
- Comparison table: Competitor | Their Strength | Their Weakness | Your Angle

## 7. Timing Signal Triangulation
Cross-reference ALL sources to score urgency (1-10) and build the "Why Now" case:
- Funding + headcount growth = budget (cite Apollo + News)
- New leadership + hiring = tool re-evaluation window (cite Apollo + Careers)
- Product launch + blog posts = active investment area (cite Blog + News)
- Competitor mentions + review sentiment = switching consideration (cite Tavily)

Synthesise into a "**Bottom Line: Why This Week**" paragraph.

## 8. Recommended Battle Plan
Deeply personalised and comprehensive:
- 5 opening hooks (each cites a specific finding with source)
- 5 pain points to probe (mapped to hiring signals, tech gaps, or initiatives)
- 5 likely objections + responses (tied to their competitive landscape)
- Strategic outreach sequence: who to email first, what subject line, \
  what to reference in each message
- Follow-up strategy: what to send after the first call"""


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
                           tier="base"):
    ctx = (
        f"**Seller's context:** {context}\n"
        "Tailor EVERY section to this seller's specific situation. "
        "Every recommendation must explain how it helps THIS seller "
        "close THIS deal."
    ) if context else ""

    template = TIER_TEMPLATES.get(tier, SYNTHESIS_USER_BASE)

    return template.format(
        company=company,
        context_block=ctx,
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
