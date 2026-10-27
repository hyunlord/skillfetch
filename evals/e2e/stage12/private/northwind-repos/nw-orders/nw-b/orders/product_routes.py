"""Product API routes."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from lib.nwids import new as nwids_new
from lib.nwlog import event as nwlog_event
from orders.database import get_db

router = APIRouter()


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/products")
def list_products(cursor: str | None = None, limit: int = Query(default=20, le=100)):
    trace_id = str(uuid4())
    nwlog_event("products.listed", tenant_id="", trace_id=trace_id, cursor=cursor, limit=limit)
    db = get_db()
    try:
        if cursor:
            rows = db.execute(
                "SELECT * FROM products WHERE id > ? ORDER BY id LIMIT ?",
                (int(cursor), limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM products ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r["public_id"],
                "name": r["name"],
                "description": r["description"],
                "price_minor": r["price_minor"],
                "currency": r["currency"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        next_cursor = str(rows[-1]["id"]) if len(rows) == limit else None
        return {"data": items, "next_cursor": next_cursor}
    finally:
        db.close()


@router.get("/products/{public_id}")
def get_product(public_id: str):
    trace_id = str(uuid4())
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM products WHERE public_id = ?", (public_id,)
        ).fetchone()
        if not row:
            nwlog_event(
                "products.not_found",
                tenant_id="",
                trace_id=trace_id,
                public_id=public_id,
            )
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "NW-PROD-001",
                        "message": "Product not found",
                        "trace_id": trace_id,
                    }
                },
            )
        nwlog_event(
            "products.retrieved",
            tenant_id="",
            trace_id=trace_id,
            public_id=public_id,
        )
        return {
            "id": row["public_id"],
            "name": row["name"],
            "description": row["description"],
            "price_minor": row["price_minor"],
            "currency": row["currency"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        db.close()
