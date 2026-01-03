# app/models/payment.py
from decimal import Decimal

from app.models.base_model import BaseSqlModel
from sqlmodel import Column, Field, String


class Payment(BaseSqlModel, table=True):
    """
    Payment model with unique constraints for:
    - Idempotency (prevent duplicate requests)
    - Transaction deduplication (prevent duplicate charges)
    """

    __tablename__ = "payments"

    id: int | None = Field(default=None, primary_key=True)

    idempotency_key: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )

    # User info
    user_id: int = Field(index=True)

    # Payment details
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)

    # Status tracking
    status: str = Field(default="pending")  # pending, processing, completed, failed

    # External transaction tracking (for deduplication)
    transaction_id: str | None = Field(
        default=None, sa_column=Column(String(255), unique=True, index=True)
    )

    # Gateway response
    gateway_response: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
