from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderRequest(BaseModel):
    """Request model for creating order"""

    user_id: int
    total: Decimal
    currency: str = "USD"
    items: str
    idempotency_key: str | None = None


class OrderResponse(BaseModel):
    """Response model for order"""

    id: int
    idempotency_key: str
    user_id: int
    payment_id: int | None
    total: Decimal
    currency: str
    status: str
    created_at: datetime
    message: str
