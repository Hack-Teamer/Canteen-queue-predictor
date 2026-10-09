from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.websocket_manager import ws_manager
from app.models.notification import Notification
from app.repositories.analytics_repo import AnalyticsRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnalyticsRepository(session)

    async def notify_user(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        type: str = "order_update",
        order_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            order_id=order_id,
            title=title,
            body=body,
            type=type,
            sent_at=datetime.now(timezone.utc),
        )
        saved_notif = await self.repo.create_notification(notif)

        # Real-time WebSocket dispatch
        payload = {
            "type": "notification",
            "notification_id": str(saved_notif.id),
            "order_id": str(order_id) if order_id else None,
            "title": title,
            "body": body,
            "sent_at": saved_notif.sent_at.isoformat(),
        }
        await ws_manager.send_to_user(str(user_id), payload)
        logger.info(f"Notification sent to user {user_id}: {title}")
        return saved_notif

    async def get_user_notifications(self, user_id: uuid.UUID) -> List[Notification]:
        return await self.repo.get_user_notifications(user_id)

    async def mark_as_read(self, notif_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        return await self.repo.mark_notification_read(notif_id, user_id)

    async def register_device_token(self, user_id: uuid.UUID, token: str, platform: str) -> None:
        await self.repo.upsert_device_token(user_id, token, platform)
