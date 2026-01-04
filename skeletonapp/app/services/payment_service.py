# app/services/payment_service.py - FIXED VERSION
import logging
import stripe
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

# Configure Stripe
stripe.api_key = settings.payment_gateway_api_key


class PaymentGatewayError(Exception):
    """Custom exception for payment gateway failures"""
    pass


class PaymentService:
    """
    Payment processing service with Stripe
    """

    async def process_payment(
        self,
        payment_request: PaymentRequest,
        session: AsyncSession,
        auto_commit: bool = True  # ✅ NEW: Control commit behavior
    ) -> PaymentResponse:
        """
        Process payment with full reliability patterns
        
        Args:
            payment_request: Payment details
            session: Database session
            auto_commit: If True (default), commits transaction.
                        If False, only flushes (for use within another transaction).
        """
        # Generate idempotency key if not provided
        idempotency_key = (
            payment_request.idempotency_key
            or self._generate_idempotency_key(payment_request)
        )

        # IDEMPOTENCY CHECK
        existing_payment = await self._find_by_idempotency_key(session, idempotency_key)
        if existing_payment:
            logger.info(f"Idempotent request detected: {idempotency_key}")
            return self._to_response(
                existing_payment, "Payment already processed (idempotent)"
            )

        # TRANSACTIONAL PROCESSING
        payment = await self._create_payment_record(
            payment_request, idempotency_key, session, auto_commit=False  # ✅ Never commit here
        )

        try:
            # Charge via Stripe SDK
            charge = await self._charge_with_stripe(payment_request, idempotency_key)

            # DEDUPLICATION CHECK
            if await self._transaction_exists(session, charge.id):
                logger.warning(f"Duplicate transaction detected: {charge.id}")
                payment.status = "failed"
                payment.error_message = "Duplicate transaction"
                payment.updated_at = utc_now()
                
                # ✅ FIXED: Conditional commit
                if auto_commit:
                    await session.commit()
                else:
                    await session.flush()
                    
                raise ValueError("Duplicate transaction detected")

            # Update payment with success
            payment.transaction_id = charge.id
            payment.status = "completed"
            payment.gateway_response = str(charge)
            payment.updated_at = utc_now()
            
            # ✅ FIXED: Conditional commit
            if auto_commit:
                await session.commit()
                await session.refresh(payment)  # Only refresh after commit
            else:
                await session.flush()  # Just flush to persist changes

            logger.info(f"Payment processed successfully: {payment.id}")
            return self._to_response(payment, "Payment processed successfully")

        except Exception as e:
            logger.error(f"Payment processing failed: {e}")

            # Mark payment as failed
            payment.status = "failed"
            payment.error_message = str(e)
            payment.updated_at = utc_now()
            
            # ✅ FIXED: Conditional commit
            if auto_commit:
                await session.commit()
            else:
                await session.flush()

            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (stripe.error.APIConnectionError, stripe.error.RateLimitError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _charge_with_stripe(
        self, payment_request: PaymentRequest, idempotency_key: str
    ):
        """
        Charge payment via Stripe API
        """
        try:
            logger.info(f"Creating Stripe charge for ${payment_request.amount}")

            payment_intent = stripe.PaymentIntent.create(
                amount=int(payment_request.amount * 100),  # cents
                currency=payment_request.currency.lower(),
                payment_method_types=["card"],
                description=f"Payment for user {payment_request.user_id}",
                metadata={
                    "user_id": str(payment_request.user_id),
                    "idempotency_key": idempotency_key,
                },
                idempotency_key=idempotency_key,
                confirm=True,
                payment_method="pm_card_visa",  # Test payment method
            )

            logger.info(f"Stripe PaymentIntent created: {payment_intent.id}")
            return payment_intent

        except stripe.error.CardError as e:
            logger.error(f"Card declined: {e.user_message}")
            raise PaymentGatewayError(f"Card declined: {e.user_message}")

        except stripe.error.RateLimitError as e:
            logger.error(f"Stripe rate limit: {e}")
            raise

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid request: {e}")
            raise PaymentGatewayError(f"Invalid request: {e}")

        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe authentication failed: {e}")
            raise PaymentGatewayError("Payment gateway authentication failed")

        except stripe.error.APIConnectionError as e:
            logger.error(f"Network error: {e}")
            raise

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise PaymentGatewayError(f"Payment processing error: {e}")

    async def _create_payment_record(
        self,
        payment_request: PaymentRequest,
        idempotency_key: str,
        session: AsyncSession,
        auto_commit: bool = False  # ✅ NEW: Don't commit by default
    ) -> Payment:
        """
        Create initial payment record in database
        
        Args:
            auto_commit: If True, commits. If False, only flushes.
        """
        payment = Payment(
            idempotency_key=idempotency_key,
            user_id=payment_request.user_id,
            amount=payment_request.amount,
            currency=payment_request.currency,
            status="processing",
        )

        session.add(payment)
        
        # ✅ FIXED: Conditional commit
        if auto_commit:
            await session.commit()
            await session.refresh(payment)
        else:
            await session.flush()  # Just get the ID

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