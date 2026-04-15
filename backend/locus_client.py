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

    async def _post(self, path: str, body: dict, timeout: int = 30,
                    raise_on_error: bool = False) -> dict:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(url, headers=self.headers, json=body)
            data = self._decode_response(r, path, "POST", raise_on_error=raise_on_error)
            return data

    async def _get(self, path: str, timeout: int = 15,
                   raise_on_error: bool = False) -> dict:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url, headers=self.headers)
            return self._decode_response(r, path, "GET", raise_on_error=raise_on_error)

    def _decode_response(self, response: httpx.Response, path: str, method: str,
                         *, raise_on_error: bool) -> dict:
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"{method} {path} returned non-JSON response ({response.status_code})"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"{method} {path} returned unexpected response shape")

        ok = response.is_success and data.get("success", True)
        pending_approval = (
            response.status_code == 202
            or data.get("status") == "PENDING_APPROVAL"
            or data.get("data", {}).get("status") == "PENDING_APPROVAL"
        )

        if not ok:
            message = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
            log.warning("%s %s → %s", method, path, message)
            if raise_on_error:
                raise RuntimeError(f"{method} {path} failed: {message}")

        if pending_approval and raise_on_error:
            approval_url = (
                data.get("approval_url")
                or data.get("data", {}).get("approval_url")
                or "approval required"
            )
            raise RuntimeError(f"{method} {path} is pending manual approval: {approval_url}")

        return data

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
        return await self._post("/wrapped/apollo/org-enrichment", body, raise_on_error=True)

    async def apollo_people_search(self, domain: str) -> dict:
        return await self._post("/wrapped/apollo/people-search", {
            "q_organization_domains": [domain],
            "person_seniorities": ["founder", "c_suite", "vp", "director", "head"],
            "per_page": 10,
        }, raise_on_error=True)

    # ── wrapped: Hunter ──

    async def hunter_domain_search(self, domain: str) -> dict:
        return await self._post("/wrapped/hunter/domain-search", {
            "domain": domain,
            "limit": 10,
        }, raise_on_error=True)

    # ── wrapped: BuiltWith ──

    async def builtwith_lookup(self, domain: str) -> dict:
        return await self._post("/wrapped/builtwith/free", {"LOOKUP": domain}, raise_on_error=True)

    # ── wrapped: Firecrawl ──

    async def firecrawl_scrape(self, url: str) -> dict:
        return await self._post("/wrapped/firecrawl/scrape", {
            "url": url,
            "formats": ["markdown"],
        }, timeout=45, raise_on_error=True)

    # ── wrapped: Tavily ──

    async def tavily_search(self, query: str, max_results: int = 5,
                            topic: str = "general") -> dict:
        return await self._post("/wrapped/tavily/search", {
            "query": query,
            "search_depth": "basic",
            "topic": topic,
            "max_results": max_results,
            "include_answer": True,
        }, raise_on_error=True)

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
        }, timeout=90, raise_on_error=True)

    # ── AgentMail ──

    async def send_email(self, inbox_id: str, to_email: str, subject: str, body: str) -> dict:
        return await self._post("/x402/agentmail-send-message", {
            "inbox_id": inbox_id,
            "to": [{"email": to_email}],
            "subject": subject,
            "body": body,
        })

    # ── checkout (merchant) ──

    async def create_checkout_session(self, *, amount: str, description: str,
                                      success_url: str, cancel_url: str,
                                      order_id: str) -> dict:
        return await self._post("/checkout/sessions", {
            "amount": amount,
            "currency": "USDC",
            "description": description,
            "successUrl": success_url,
            "cancelUrl": cancel_url,
            "metadata": {"order_id": order_id},
        })

    async def get_checkout_session(self, session_id: str) -> dict:
        return await self._get(f"/checkout/sessions/{session_id}")

    # ── transactions ──

    async def get_transactions(self, limit: int = 50) -> dict:
        return await self._get(f"/pay/transactions?limit={limit}")
