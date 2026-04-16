import sqlite3
import uuid
from datetime import datetime, timezone

from config import DATABASE_PATH


def _conn():
    c = sqlite3.connect(DATABASE_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = _conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id                    TEXT PRIMARY KEY,
            company_name          TEXT NOT NULL,
            company_domain        TEXT DEFAULT '',
            context               TEXT DEFAULT '',
            client_email          TEXT NOT NULL,
            tier                  TEXT DEFAULT 'base',
            status                TEXT DEFAULT 'AWAITING_PAYMENT',
            checkout_session_id   TEXT DEFAULT '',
            company_data          TEXT DEFAULT '{}',
            people_data           TEXT DEFAULT '{}',
            tech_data             TEXT DEFAULT '{}',
            website_data          TEXT DEFAULT '{}',
            careers_data          TEXT DEFAULT '{}',
            blog_data             TEXT DEFAULT '{}',
            news_data             TEXT DEFAULT '{}',
            hiring_data           TEXT DEFAULT '{}',
            competitor_data       TEXT DEFAULT '{}',
            report                TEXT DEFAULT '',
            revenue               REAL DEFAULT 0.0,
            total_cost            REAL DEFAULT 0.0,
            cost_breakdown        TEXT DEFAULT '{}',
            addons_purchased      TEXT DEFAULT '[]',
            pending_action        TEXT DEFAULT '',
            created_at            TEXT NOT NULL,
            paid_at               TEXT,
            completed_at          TEXT,
            error                 TEXT DEFAULT ''
        )
    """)
    # migrate existing DBs that lack newer columns
    for col, definition in [
        ("checkout_session_id", "TEXT DEFAULT ''"),
        ("tier",                "TEXT DEFAULT 'base'"),
        ("careers_data",        "TEXT DEFAULT '{}'"),
        ("blog_data",           "TEXT DEFAULT '{}'"),
        ("hiring_data",         "TEXT DEFAULT '{}'"),
        ("competitor_data",     "TEXT DEFAULT '{}'"),
        ("addons_purchased",    "TEXT DEFAULT '[]'"),
        ("pending_action",      "TEXT DEFAULT ''"),
        ("enrichment_log",      "TEXT DEFAULT '[]'"),
    ]:
        try:
            c.execute(f"ALTER TABLE orders ADD COLUMN {col} {definition}")
            c.commit()
        except Exception:
            pass
    c.commit()
    c.close()


def create_order(company_name, company_domain, context, client_email, revenue, tier="base"):
    c = _conn()
    oid = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        """INSERT INTO orders
           (id, company_name, company_domain, context, client_email, tier, status, revenue, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (oid, company_name, company_domain, context, client_email, tier, "AWAITING_PAYMENT", revenue, now),
    )
    c.commit()
    c.close()
    return oid


def get_order(oid):
    c = _conn()
    row = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    c.close()
    return dict(row) if row else None


def update_order(oid, **kw):
    c = _conn()
    sets = ", ".join(f"{k}=?" for k in kw)
    c.execute(f"UPDATE orders SET {sets} WHERE id=?", [*kw.values(), oid])
    c.commit()
    c.close()


def get_all_orders():
    c = _conn()
    rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_orders_by_email(email):
    c = _conn()
    rows = c.execute(
        "SELECT id, company_name, company_domain, tier, status, revenue, created_at, completed_at"
        " FROM orders WHERE LOWER(client_email)=? ORDER BY created_at DESC",
        (email.strip().lower(),),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_dashboard_stats():
    c = _conn()
    row = c.execute("""
        SELECT
            COUNT(*)                                                   AS total_orders,
            SUM(CASE WHEN status='COMPLETED'  THEN 1 ELSE 0 END)      AS completed,
            SUM(CASE WHEN status='PROCESSING' THEN 1 ELSE 0 END)      AS processing,
            SUM(CASE WHEN status='FAILED'     THEN 1 ELSE 0 END)      AS failed,
            COALESCE(SUM(CASE WHEN status='COMPLETED' THEN revenue  ELSE 0 END), 0) AS total_revenue,
            COALESCE(SUM(total_cost), 0)                               AS total_cost
        FROM orders
    """).fetchone()
    c.close()
    return dict(row)
