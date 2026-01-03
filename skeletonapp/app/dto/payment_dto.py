from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentRequest(BaseModel):
    """Request model for creating payment"""

    user_id: int
    amount: Decimal
    currency: str = "USD"
    idempotency_key: str | None = None


class PaymentResponse(BaseModel):
    """Response model for payment"""

    id: int
    idempotency_key: str
    user_id: int
    amount: Decimal
    currency: str
    status: str
    transaction_id: str | None
    created_at: datetime
    message: str
