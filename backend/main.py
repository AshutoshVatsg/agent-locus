"""
BriefBot — AI Sales Briefing Agent
Powered by Locus (beta.paywithlocus.com)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import markdown as md_lib

from config import (
    SERVER_URL, TIER_CONFIG, TIER_ORDER, AGENTMAIL_INBOX_ID, ADMIN_KEY,
    ADDONS, get_upgrade_price, get_available_addons, get_available_upgrades,
)
from database import init_db, create_order, get_order, get_all_orders, get_orders_by_email, get_dashboard_stats, update_order
from locus_client import LocusClient
from pipeline import run_pipeline, run_addon, run_upgrade

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("briefbot")

app = FastAPI(title="BriefBot", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def _require_admin(request: Request):
    key = request.headers.get("x-admin-key", "")
    if key != ADMIN_KEY:
        raise HTTPException(403, "Unauthorized")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ────────────────────────── Models ──────────────────────────


class OrderIn(BaseModel):
    company_name: str
    company_domain: str = ""
    context: str = ""
    client_email: str
    tier: str = "base"


class AddonIn(BaseModel):
    addon_key: str


class UpgradeIn(BaseModel):
    target_tier: str


# ────────────────────────── Core API ──────────────────────────


@app.post("/api/orders")
async def api_create_order(body: OrderIn):
    tier = body.tier if body.tier in TIER_CONFIG else "base"
    price = TIER_CONFIG[tier]["price"]

    oid = create_order(
        body.company_name,
        body.company_domain.strip().lower(),
        body.context,
        body.client_email,
        price,
        tier,
    )
    locus = LocusClient()
    tier_label = TIER_CONFIG[tier]["label"]
    session = await locus.create_checkout_session(
        amount=str(price),
        description=f"BriefBot {tier_label} Briefing — {body.company_name}",
        success_url=f"{SERVER_URL}/report/{oid}",
        cancel_url=f"{SERVER_URL}/",
        order_id=oid,
    )
    if not session.get("success"):
        update_order(oid, status="FAILED", error="Failed to create payment session")
        raise HTTPException(500, "Could not create payment session")

    checkout_url = session["data"]["checkoutUrl"]
    checkout_session_id = session["data"]["id"]
    update_order(oid, checkout_session_id=checkout_session_id)

    return {"order_id": oid, "price": price, "tier": tier, "checkout_url": checkout_url}


@app.get("/api/orders/{oid}")
async def api_get_order(oid: str, bg: BackgroundTasks):
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")

    locus = LocusClient()

    # ── check initial payment ──
    if order["status"] == "AWAITING_PAYMENT" and order.get("checkout_session_id"):
        try:
            session = await locus.get_checkout_session(order["checkout_session_id"])
            if session.get("success") and session["data"]["status"] == "PAID":
                now = datetime.now(timezone.utc).isoformat()
                update_order(oid, status="PROCESSING", paid_at=now)
                order["status"] = "PROCESSING"
                order["paid_at"] = now
                bg.add_task(
                    run_pipeline, oid, order["company_name"],
                    order["company_domain"], order["context"],
                    order.get("tier", "base"),
                )
        except Exception as e:
            log.warning("Payment check failed for %s: %s", oid, e)

    # ── check pending add-on / upgrade payment ──
    pending_raw = order.get("pending_action") or ""
    if pending_raw and order["status"] == "COMPLETED":
        try:
            pending = json.loads(pending_raw)
            csid = pending.get("checkout_session_id")
            if csid:
                session = await locus.get_checkout_session(csid)
                if session.get("success"):
                    sess_status = session["data"]["status"]
                    if sess_status == "PAID":
                        if pending["type"] == "addon":
                            update_order(oid, status="PROCESSING", pending_action=pending_raw)
                            order["status"] = "PROCESSING"
                            bg.add_task(run_addon, oid, pending["key"])
                        elif pending["type"] == "upgrade":
                            update_order(oid, status="PROCESSING", pending_action=pending_raw)
                            order["status"] = "PROCESSING"
                            bg.add_task(run_upgrade, oid, pending["tier"])
                    elif sess_status in ("EXPIRED", "CANCELLED"):
                        # Checkout abandoned or expired — clear so user can retry
                        update_order(oid, pending_action="")
                        order["pending_action"] = ""
                    # else PENDING — still waiting, leave pending_action intact
        except Exception as e:
            log.warning("Pending action check failed for %s: %s", oid, e)

    return order


# ────────────────────────── Pending Action ──────────────────────────


@app.post("/api/orders/{oid}/cancel-pending")
async def api_cancel_pending(oid: str):
    """Cancel an unpaid add-on / upgrade checkout so the user can retry."""
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")
    if not order.get("pending_action"):
        return {"cleared": True}
    update_order(oid, pending_action="")
    return {"cleared": True}


# ────────────────────────── Add-ons & Upgrades ──────────────────────────


@app.get("/api/orders/{oid}/options")
async def api_get_options(oid: str):
    """Return available add-ons and tier upgrades for this order."""
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")

    current_tier = order.get("tier", "base")
    purchased = json.loads(order.get("addons_purchased") or "[]")

    return {
        "current_tier": current_tier,
        "addons": get_available_addons(current_tier, purchased),
        "upgrades": get_available_upgrades(current_tier),
        "purchased_addons": purchased,
    }


@app.post("/api/orders/{oid}/addon")
async def api_purchase_addon(oid: str, body: AddonIn):
    """Create a checkout session for an individual add-on."""
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] != "COMPLETED":
        raise HTTPException(400, "Report must be completed before adding sections")

    addon_key = body.addon_key
    if addon_key not in ADDONS:
        raise HTTPException(400, f"Unknown add-on: {addon_key}")

    purchased = json.loads(order.get("addons_purchased") or "[]")
    if addon_key in purchased:
        raise HTTPException(400, "Add-on already purchased")

    addon = ADDONS[addon_key]
    locus = LocusClient()

    session = await locus.create_checkout_session(
        amount=str(addon["price"]),
        description=f"BriefBot Add-on: {addon['label']} — {order['company_name']}",
        success_url=f"{SERVER_URL}/report/{oid}",
        cancel_url=f"{SERVER_URL}/report/{oid}",
        order_id=f"{oid}_addon_{addon_key}",
    )
    if not session.get("success"):
        raise HTTPException(500, "Could not create payment session")

    checkout_url = session["data"]["checkoutUrl"]
    checkout_session_id = session["data"]["id"]

    # store pending action
    pending = json.dumps({
        "type": "addon",
        "key": addon_key,
        "checkout_session_id": checkout_session_id,
    })
    update_order(oid, pending_action=pending)

    return {
        "addon_key": addon_key,
        "price": addon["price"],
        "checkout_url": checkout_url,
    }


@app.post("/api/orders/{oid}/upgrade")
async def api_purchase_upgrade(oid: str, body: UpgradeIn):
    """Create a checkout session to upgrade to a higher tier."""
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] != "COMPLETED":
        raise HTTPException(400, "Report must be completed before upgrading")

    current_tier = order.get("tier", "base")
    target_tier = body.target_tier

    if target_tier not in TIER_CONFIG:
        raise HTTPException(400, f"Unknown tier: {target_tier}")
    if TIER_ORDER.index(target_tier) <= TIER_ORDER.index(current_tier):
        raise HTTPException(400, "Can only upgrade to a higher tier")

    price = get_upgrade_price(current_tier, target_tier)
    if price <= 0:
        raise HTTPException(400, "No upgrade needed")

    locus = LocusClient()
    target_label = TIER_CONFIG[target_tier]["label"]

    session = await locus.create_checkout_session(
        amount=str(price),
        description=f"BriefBot Upgrade to {target_label} — {order['company_name']}",
        success_url=f"{SERVER_URL}/report/{oid}",
        cancel_url=f"{SERVER_URL}/report/{oid}",
        order_id=f"{oid}_upgrade_{target_tier}",
    )
    if not session.get("success"):
        raise HTTPException(500, "Could not create payment session")

    checkout_url = session["data"]["checkoutUrl"]
    checkout_session_id = session["data"]["id"]

    pending = json.dumps({
        "type": "upgrade",
        "tier": target_tier,
        "checkout_session_id": checkout_session_id,
    })
    update_order(oid, pending_action=pending)

    return {
        "target_tier": target_tier,
        "price": price,
        "full_price": TIER_CONFIG[target_tier]["price"],
        "checkout_url": checkout_url,
    }


# ────────────────────────── Email ──────────────────────────


@app.post("/api/orders/{oid}/send-email")
async def api_send_email(oid: str):
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] != "COMPLETED":
        raise HTTPException(400, "Report not ready yet")
    if not AGENTMAIL_INBOX_ID:
        raise HTTPException(503, "Email delivery not configured")

    tier_label = TIER_CONFIG.get(order.get("tier", "base"), {}).get("label", "Base")
    subject = f"Your BriefBot {tier_label} Report — {order['company_name']}"

    report_html = md_lib.markdown(order["report"], extensions=["tables"])
    body = f"""<html><body style="font-family:sans-serif;max-width:700px;margin:auto;color:#1e293b">
<h2 style="color:#4f46e5">BriefBot {tier_label} Sales Briefing</h2>
<p><strong>Company:</strong> {order['company_name']} &nbsp;|&nbsp;
   <strong>Domain:</strong> {order['company_domain'] or '—'}</p>
<hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0"/>
{report_html}
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0"/>
<p style="font-size:12px;color:#94a3b8">
  Generated by <a href="https://briefbot.ai" style="color:#6366f1">BriefBot</a> —
  powered by <a href="https://beta.paywithlocus.com" style="color:#6366f1">Locus</a>
</p>
</body></html>"""

    try:
        locus = LocusClient()
        result = await locus.send_email(
            inbox_id=AGENTMAIL_INBOX_ID,
            to_email=order["client_email"],
            subject=subject,
            body=body,
        )
        if not result.get("success"):
            raise HTTPException(500, result.get("message", "Email send failed"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"sent": True, "to": order["client_email"]}


# ────────────────────────── Client Order History ──────────────────────────


@app.get("/api/my-orders")
async def api_my_orders(email: str = ""):
    """Public endpoint — returns a client's past orders (no sensitive data)."""
    email = email.strip()
    if not email:
        raise HTTPException(400, "Email is required")
    return get_orders_by_email(email)


# ────────────────────────── Dashboard ──────────────────────────


@app.get("/api/orders")
async def api_list_orders(request: Request):
    _require_admin(request)
    return get_all_orders()


@app.get("/api/dashboard")
async def api_dashboard(request: Request):
    _require_admin(request)
    stats = get_dashboard_stats()
    try:
        locus = LocusClient()
        bal = await locus.get_balance()
        stats["wallet_balance"] = bal.get("data", {}).get("usdc_balance", "0.00")
        stats["wallet_address"] = bal.get("data", {}).get("wallet_address", "")
    except Exception:
        stats["wallet_balance"] = "N/A"
        stats["wallet_address"] = ""
    stats["report_price"] = TIER_CONFIG["base"]["price"]
    stats["tiers"] = TIER_CONFIG
    return stats


@app.get("/api/tiers")
async def api_tiers():
    """Public endpoint — just tier pricing for the storefront."""
    return {"tiers": TIER_CONFIG}


# ────────────────────────── Frontend ──────────────────────────


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
async def page_index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/report/{oid}")
async def page_report(oid: str):
    return FileResponse(FRONTEND / "report.html")


@app.get("/my-orders")
async def page_my_orders():
    return FileResponse(FRONTEND / "my-orders.html")


@app.get("/dashboard")
async def page_dashboard():
    return FileResponse(FRONTEND / "dashboard.html")
