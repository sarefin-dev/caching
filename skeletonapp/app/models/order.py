# app/models/order.py
from sqlmodel import Field, Column, String
from decimal import Decimal
from app.models.base_model import BaseSqlModel


class Order(BaseSqlModel, table=True):
    """Order model"""

    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)

    # Idempotency
    idempotency_key: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )

    # User and payment reference
    user_id: int = Field(index=True)
    payment_id: int | None = Field(default=None, foreign_key="payments.id")

    # Order details
    total: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    items: str = Field()  # JSON string of items

    # Status
    status: str = Field(default="pending")  # pending, confirmed, cancelled, failed
