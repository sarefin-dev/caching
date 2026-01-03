# app/api/payments.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.core.database import get_session
from app.dto.payment_dto import PaymentRequest, PaymentResponse
from app.services.payment_service import PaymentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/payments", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payment_request: PaymentRequest,
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a payment with full reliability guarantees
    
    Features:
    - Idempotency: Same request returns same result
    - Deduplication: Detects duplicate transactions
    - Retries: Auto-retries failed gateway calls
    - Transactions: All-or-nothing database operations
    - Timeouts: Won't hang forever
    
    Headers:
        Idempotency-Key: Optional client-provided idempotency key
    
    Example:
        POST /api/payments
        Headers: Idempotency-Key: abc123
        Body: {"user_id": 1, "amount": 99.99, "currency": "USD"}
    """
    # Use header idempotency key if provided
    if idempotency_key:
        payment_request.idempotency_key = idempotency_key
    
    try:
        payment_service = PaymentService()
        result = await payment_service.process_payment(payment_request, session)
        return result
        
    except Exception as e:
        logger.error(f"Payment creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Payment processing failed: {str(e)}"
        )