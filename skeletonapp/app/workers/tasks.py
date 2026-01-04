# app/workers/tasks.py
from celery import Celery
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'payment_service',
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Reliability settings
    task_acks_late=True,  # At-least-once delivery
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max
    task_max_retries=3,
)


@celery_app.task(bind=True)
def send_order_confirmation(self, order_id: int):
    """
    Send order confirmation email
    
    Celery handles:
    - Retries with backoff
    - At-least-once delivery
    - Timeouts
    """
    try:
        logger.info(f"Sending order confirmation for order {order_id}")
        
        # In production, use actual email service (SendGrid, SES, etc.)
        # For now, just log
        logger.info(f"Email sent for order {order_id}")
        
        return {"status": "sent", "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Failed to send email for order {order_id}: {e}")
        raise  # Celery will retry