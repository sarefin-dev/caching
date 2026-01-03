# app/api/orders.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.core.database import get_session
from app.dto.order_dto import OrderRequest, OrderResponse
from app.services.order_service import OrderService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    order_request: OrderRequest,
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create an order with payment
    
    Demonstrates TRANSACTIONAL PROCESSING:
    - Order and payment created in single database transaction
    - Both succeed or both fail (ACID)
    
    Headers:
        Idempotency-Key: Optional client-provided idempotency key
    
    Example:
        POST /api/orders
        Headers: Idempotency-Key: order-123
        Body: {
            "user_id": 1,
            "total": 99.99,
            "currency": "USD",
            "items": "[{\"product\": \"Widget\", \"qty\": 2}]"
        }
    """
    # Use header idempotency key if provided
    if idempotency_key:
        order_request.idempotency_key = idempotency_key
    
    try:
        order_service = OrderService()
        result = await order_service.create_order(order_request, session)
        return result
        
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Order processing failed: {str(e)}"
        )