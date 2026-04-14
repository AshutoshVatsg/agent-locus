"""
BriefBot — AI Sales Briefing Agent
Powered by Locus (beta.paywithlocus.com)
"""

import logging
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import REPORT_PRICE_USDC
from database import init_db, create_order, get_order, get_all_orders, get_dashboard_stats
from locus_client import LocusClient
from pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="BriefBot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
def on_startup():
    init_db()


# ────────────────────────── API ──────────────────────────


class OrderIn(BaseModel):
    company_name: str
    company_domain: str = ""
    context: str = ""
    client_email: str


@app.post("/api/orders")
async def api_create_order(body: OrderIn, bg: BackgroundTasks):
    oid = create_order(
        body.company_name,
        body.company_domain.strip().lower(),
        body.context,
        body.client_email,
        REPORT_PRICE_USDC,
    )
    bg.add_task(run_pipeline, oid, body.company_name,
                body.company_domain.strip().lower(), body.context)
    return {"order_id": oid, "price": REPORT_PRICE_USDC}


@app.get("/api/orders/{oid}")
async def api_get_order(oid: str):
    order = get_order(oid)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@app.get("/api/orders")
async def api_list_orders():
    return get_all_orders()


@app.get("/api/dashboard")
async def api_dashboard():
    stats = get_dashboard_stats()
    try:
        locus = LocusClient()
        bal = await locus.get_balance()
        stats["wallet_balance"] = bal.get("data", {}).get("usdc_balance", "0.00")
        stats["wallet_address"] = bal.get("data", {}).get("wallet_address", "")
    except Exception:
        stats["wallet_balance"] = "N/A"
        stats["wallet_address"] = ""
    stats["report_price"] = REPORT_PRICE_USDC
    return stats


# ────────────────────────── Frontend ──────────────────────────


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
async def page_index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/report/{oid}")
async def page_report(oid: str):
    return FileResponse(FRONTEND / "report.html")


@app.get("/dashboard")
async def page_dashboard():
    return FileResponse(FRONTEND / "dashboard.html")
