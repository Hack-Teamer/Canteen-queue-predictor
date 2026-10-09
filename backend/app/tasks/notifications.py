import asyncio
import uuid
from app.core.logging import logger
from app.db.session import async_session_factory
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app


async def _send_async_notification(user_id_str: str, title: str, body: str, order_id_str: str = None):
    async with async_session_factory() as session:
        service = NotificationService(session)
        user_id = uuid.UUID(user_id_str)
        order_id = uuid.UUID(order_id_str) if order_id_str else None
        await service.notify_user(user_id=user_id, title=title, body=body, order_id=order_id)


@celery_app.task(name="app.tasks.notifications.send_push_notification")
def send_push_notification(user_id: str, title: str, body: str, order_id: str = None):
    try:
        asyncio.run(_send_async_notification(user_id, title, body, order_id))
        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return {"status": "error", "message": str(e)}
