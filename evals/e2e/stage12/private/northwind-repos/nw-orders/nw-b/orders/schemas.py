"""Request and response schemas."""
from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    customer_id: int
    product: str
    quantity: int = 1
    unit_price: float


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    product: str
    quantity: int
    unit_price: float
    total: float
    currency: str
    status: str
    created_at: str
    updated_at: str
