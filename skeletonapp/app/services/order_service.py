# app/services/order_service.py
import logging

from app.dto.order_dto import OrderRequest, OrderResponse
from app.dto.payment_dto import PaymentRequest
from app.models.base_model import utc_now
from app.models.order import Order
from app.services.payment_service import PaymentService
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)


class OrderService:
    """
    Order processing service

    Demonstrates TRANSACTIONAL PROCESSING across order + payment
    """

    def __init__(self):
        self.payment_service = PaymentService()

    async def create_order(
        self, order_request: OrderRequest, session: AsyncSession
    ) -> OrderResponse:
        """
        Create order with payment in SINGLE TRANSACTION
        """
        # Generate idempotency key
        idempotency_key = (
            order_request.idempotency_key
            or self._generate_idempotency_key(order_request)
        )

        # Check if order already exists
        existing_order = await self._find_by_idempotency_key(session, idempotency_key)
        if existing_order:
            logger.info(f"Idempotent order request: {idempotency_key}")
            return self._to_response(existing_order, "Order already exists")

        try:
            async with session.begin_nested():  # Savepoint - auto-commits on success
                # 1. Create order
                order = Order(
                    idempotency_key=idempotency_key,
                    user_id=order_request.user_id,
                    total=order_request.total,
                    currency=order_request.currency,
                    items=order_request.items,
                    status="pending_payment",
                )
                session.add(order)
                await session.flush()  # Get order.id

                logger.info("Processing order...")

                # 2. Process payment (in same transaction!)
                payment_request = PaymentRequest(
                    user_id=order_request.user_id,
                    amount=order_request.total,
                    currency=order_request.currency,
                    idempotency_key=f"ord_{order.id}_pay",
                )

                logger.info("Processing payment...")

                payment_response = await self.payment_service.process_payment(
                    payment_request,
                    session,  # Same session = same transaction!
                    auto_commit=False,
                )

                logger.info("Payment processed successfully")

                # 3. Update order with payment
                order.payment_id = payment_response.id
                order.status = "confirmed"
                order.updated_at = utc_now()

            await session.refresh(order)

            logger.info(f"Order created successfully: {order.id}")

            # Queue notification email (async, after commit)
            from app.workers.tasks import send_order_confirmation
            send_order_confirmation.delay(order.id)

            return self._to_response(order, "Order created successfully")

        except Exception as e:
            logger.error(f"❌ Order creation failed: {e}", exc_info=True)
            raise

    async def _find_by_idempotency_key(
        self, session: AsyncSession, idempotency_key: str
    ) -> Order | None:
        """Find existing order by idempotency key"""
        result = await session.exec(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        return result.one_or_none()

    def _generate_idempotency_key(self, order_request: OrderRequest) -> str:
        """Generate idempotency key"""
        import uuid

        return f"ord_{order_request.user_id}_{uuid.uuid4().hex[:16]}"

    def _to_response(self, order: Order, message: str) -> OrderResponse:
        """Convert Order to response"""
        return OrderResponse(
            id=order.id,
            idempotency_key=order.idempotency_key,
            user_id=order.user_id,
            payment_id=order.payment_id,
            total=order.total,
            currency=order.currency,
            status=order.status,
            created_at=order.created_at,
            message=message,
        )
