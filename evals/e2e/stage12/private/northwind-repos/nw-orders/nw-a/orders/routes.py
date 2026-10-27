"""Order API routes."""
from datetime import datetime

from fastapi import APIRouter, HTTPException

from .database import get_db
from .pricing import calculate_total
from .schemas import CreateOrderRequest, OrderResponse

router = APIRouter()


@router.post("/orders", response_model=OrderResponse)
def create_order(req: CreateOrderRequest):
    total = calculate_total(req.unit_price, req.quantity)
    now = datetime.utcnow().isoformat()
    db = get_db()
    cursor = db.execute(
        "INSERT INTO orders (customer_id, product, quantity, unit_price, total, currency, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (req.customer_id, req.product, req.quantity, req.unit_price, total, "USD", "pending", now, now),
    )
    order_id = cursor.lastrowid
    db.commit()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    db.close()
    print(f"Order created: {order_id}")
    return dict(row)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(row)
