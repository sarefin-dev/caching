# app/services/payment_service.py
import logging

import httpx
from app.core.config import get_settings
from app.dto.payment_dto import PaymentRequest, PaymentResponse
from app.models.base_model import utc_now
from app.models.payment import Payment
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PaymentGatewayError(Exception):
    """Custom exception for payment gateway failures"""

    pass


class PaymentService:
    """
    Payment processing service with:
    - Idempotency
    - Deduplication
    - Retry with backoff
    - Transactions
    - Timeouts
    """

    async def process_payment(
        self, payment_request: PaymentRequest, session: AsyncSession
    ) -> PaymentResponse:
        """
        Process payment with full reliability patterns

        1. Check idempotency (already processed?)
        2. Create payment record (transaction)
        3. Call payment gateway (retry + timeout)
        4. Update payment status (transaction)
        """
        # Generate idempotency key if not provided
        idempotency_key = (
            payment_request.idempotency_key
            or self._generate_idempotency_key(payment_request)
        )

        # IDEMPOTENCY CHECK: Return existing payment if already processed
        existing_payment = await self._find_by_idempotency_key(session, idempotency_key)
        if existing_payment:
            logger.info(f"Idempotent request detected: {idempotency_key}")
            return self._to_response(
                existing_payment, "Payment already processed (idempotent)"
            )

        # TRANSACTIONAL PROCESSING: Create payment in database
        payment = await self._create_payment_record(
            payment_request, idempotency_key, session
        )

        try:
            # RETRY WITH BACKOFF: Call external payment gateway
            transaction_id = await self._charge_payment_gateway(payment_request)

            # DEDUPLICATION CHECK: Ensure transaction_id is unique
            if await self._transaction_exists(session, transaction_id):
                logger.warning(f"Duplicate transaction detected: {transaction_id}")
                payment.status = "failed"
                payment.error_message = "Duplicate transaction"
                await session.commit()
                raise ValueError("Duplicate transaction detected")

            # Update payment with success
            payment.transaction_id = transaction_id
            payment.status = "completed"
            payment.updated_at = utc_now()
            await session.commit()

            logger.info(f"Payment processed successfully: {payment.id}")
            return self._to_response(payment, "Payment processed successfully")

        except Exception as e:
            logger.error(f"Payment processing failed: {e}")

            # Mark payment as failed
            payment.status = "failed"
            payment.error_message = str(e)
            payment.updated_at = utc_now()
            await session.commit()

            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PaymentGatewayError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _charge_payment_gateway(self, payment_request: PaymentRequest) -> str:
        """
        Call external payment gateway with:
        - TIMEOUT: Don't wait forever
        - RETRY WITH BACKOFF: Automatic retries with exponential backoff
        """
        timeout = httpx.Timeout(settings.payment_gateway_timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                logger.info(f"Calling payment gateway for ${payment_request.amount}")

                response = await client.post(
                    f"{settings.payment_gateway_url}/charges",
                    json={
                        "amount": int(payment_request.amount * 100),  # cents
                        "currency": payment_request.currency,
                        "source": "tok_visa",  # Demo token
                    },
                    headers={
                        "Authorization": f"Bearer {settings.payment_gateway_api_key}"
                    },
                )

                if response.status_code not in [200, 201]:
                    raise PaymentGatewayError(
                        f"Gateway returned {response.status_code}: {response.text}"
                    )

                result = response.json()
                return result.get("id", f"txn_{payment_request.user_id}")

            except httpx.TimeoutException:
                logger.error("Payment gateway timeout")
                raise
            except httpx.HTTPError as e:
                logger.error(f"Payment gateway HTTP error: {e}")
                raise PaymentGatewayError(str(e))

    async def _create_payment_record(
        self,
        payment_request: PaymentRequest,
        idempotency_key: str,
        session: AsyncSession,
    ) -> Payment:
        """Create initial payment record in database"""
        payment = Payment(
            idempotency_key=idempotency_key,
            user_id=payment_request.user_id,
            amount=payment_request.amount,
            currency=payment_request.currency,
            status="processing",
        )

        session.add(payment)
        await session.commit()
        await session.refresh(payment)

        return payment

    async def _find_by_idempotency_key(
        self, session: AsyncSession, idempotency_key: str
    ) -> Payment | None:
        """Find existing payment by idempotency key"""
        result = await session.exec(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.one_or_none()

    async def _transaction_exists(
        self, session: AsyncSession, transaction_id: str
    ) -> bool:
        """Check if transaction_id already exists"""
        result = await session.exec(
            select(Payment).where(Payment.transaction_id == transaction_id)
        )
        return result.one_or_none() is not None

    def _generate_idempotency_key(self, payment_request: PaymentRequest) -> str:
        """Generate idempotency key from request"""
        import uuid

        return f"pay_{payment_request.user_id}_{uuid.uuid4().hex[:16]}"

    def _to_response(self, payment: Payment, message: str) -> PaymentResponse:
        """Convert Payment model to response"""
        return PaymentResponse(
            id=payment.id,
            idempotency_key=payment.idempotency_key,
            user_id=payment.user_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            transaction_id=payment.transaction_id,
            created_at=payment.created_at,
            message=message,
        )
