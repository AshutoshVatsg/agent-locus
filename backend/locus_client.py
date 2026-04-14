import httpx
import logging

from config import LOCUS_API_KEY, LOCUS_API_BASE

log = logging.getLogger("locus")


class LocusClient:
    """Thin async wrapper around the Locus Beta API."""

    def __init__(self):
        self.base = LOCUS_API_BASE
        self.headers = {
            "Authorization": f"Bearer {LOCUS_API_KEY}",
            "Content-Type": "application/json",
        }

    # ── low-level ──

    async def _post(self, path: str, body: dict, timeout: int = 30) -> dict:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(url, headers=self.headers, json=body)
            data = r.json()
            if not data.get("success"):
                log.warning("POST %s → %s", path, data.get("error", data.get("message", "unknown")))
            return data

    async def _get(self, path: str, timeout: int = 15) -> dict:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url, headers=self.headers)
            return r.json()

    # ── wallet ──

    async def get_balance(self) -> dict:
        return await self._get("/pay/balance")

    # ── wrapped: Apollo ──

    async def apollo_org_enrichment(self, *, domain: str = "", name: str = "") -> dict:
        body: dict = {}
        if domain:
            body["domain"] = domain
        if name:
            body["organization_name"] = name
        return await self._post("/wrapped/apollo/org-enrichment", body)

    async def apollo_people_search(self, domain: str) -> dict:
        return await self._post("/wrapped/apollo/people-search", {
            "q_organization_domains": [domain],
            "person_seniorities": ["founder", "c_suite", "vp", "director", "head"],
            "per_page": 10,
        })

    # ── wrapped: Hunter ──

    async def hunter_domain_search(self, domain: str) -> dict:
        return await self._post("/wrapped/hunter/domain-search", {
            "domain": domain,
            "limit": 10,
        })

    # ── wrapped: BuiltWith ──

    async def builtwith_lookup(self, domain: str) -> dict:
        return await self._post("/wrapped/builtwith/free", {"LOOKUP": domain})

    # ── wrapped: Firecrawl ──

    async def firecrawl_scrape(self, url: str) -> dict:
        return await self._post("/wrapped/firecrawl/scrape", {
            "url": url,
            "formats": ["markdown"],
        }, timeout=45)

    # ── wrapped: Tavily ──

    async def tavily_search(self, query: str, max_results: int = 5) -> dict:
        return await self._post("/wrapped/tavily/search", {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": True,
        })

    # ── wrapped: OpenAI ──

    async def openai_chat(self, system: str, user: str, model: str = "gpt-4o",
                          max_tokens: int = 4000) -> dict:
        return await self._post("/wrapped/openai/chat", {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }, timeout=90)

    # ── AgentMail ──

    async def send_email(self, inbox_id: str, to_email: str, subject: str, body: str) -> dict:
        return await self._post("/x402/agentmail-send-message", {
            "inbox_id": inbox_id,
            "to": [{"email": to_email}],
            "subject": subject,
            "body": body,
        })

    # ── transactions ──

    async def get_transactions(self, limit: int = 50) -> dict:
        return await self._get(f"/pay/transactions?limit={limit}")
