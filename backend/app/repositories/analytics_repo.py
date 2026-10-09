from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.menu_item import MenuItem
from app.models.prediction import Prediction
from app.models.timetable_slot import TimetableSlot
from app.models.notification import Notification
from app.models.device_token import DeviceToken


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_today_summary(self) -> Dict[str, Any]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Total orders today
        stmt_total = select(func.count(Order.id)).where(Order.placed_at >= today_start)
        total_orders = (await self.session.execute(stmt_total)).scalar() or 0

        # Active orders now
        stmt_active = select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PLACED, OrderStatus.ACCEPTED, OrderStatus.PREPARING])
        )
        active_orders = (await self.session.execute(stmt_active)).scalar() or 0

        # Completed orders today
        stmt_completed = select(func.count(Order.id)).where(
            Order.placed_at >= today_start,
            Order.status.in_([OrderStatus.READY, OrderStatus.COLLECTED]),
        )
        completed_orders = (await self.session.execute(stmt_completed)).scalar() or 0

        # Avg wait time today
        stmt_avg_wait = select(func.avg(Prediction.actual_wait_minutes)).where(
            Prediction.created_at >= today_start,
            Prediction.actual_wait_minutes.isnot(None),
        )
        avg_wait = (await self.session.execute(stmt_avg_wait)).scalar() or 0.0

        # Total revenue today
        stmt_revenue = (
            select(func.sum(MenuItem.price * OrderItem.quantity))
            .select_from(OrderItem)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.placed_at >= today_start, Order.status != OrderStatus.CANCELLED)
        )
        revenue = (await self.session.execute(stmt_revenue)).scalar() or 0.0

        return {
            "total_orders_today": total_orders,
            "active_orders_now": active_orders,
            "completed_orders_today": completed_orders,
            "avg_wait_time_minutes": round(float(avg_wait), 1),
            "total_revenue_today": round(float(revenue), 2),
        }

    async def get_popular_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        stmt = (
            select(
                MenuItem.id,
                MenuItem.name,
                func.sum(OrderItem.quantity).label("order_count"),
                func.sum(MenuItem.price * OrderItem.quantity).label("total_revenue"),
            )
            .select_from(OrderItem)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.status != OrderStatus.CANCELLED)
            .group_by(MenuItem.id, MenuItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            items.append({
                "menu_item_id": row.id,
                "item_name": row.name,
                "order_count": int(row.order_count or 0),
                "total_revenue": round(float(row.total_revenue or 0.0), 2),
            })
        return items

    async def get_timetable_slots(self, day_of_week: int) -> List[TimetableSlot]:
        stmt = (
            select(TimetableSlot)
            .where(TimetableSlot.day_of_week == day_of_week)
            .order_by(TimetableSlot.bell_time.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # Notifications
    async def create_notification(self, notif: Notification) -> Notification:
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def get_user_notifications(self, user_id: uuid.UUID, limit: int = 20) -> List[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.sent_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_notification_read(self, notif_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        notif = result.scalar_one_or_none()
        if notif:
            notif.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return notif

    # Device Tokens
    async def upsert_device_token(self, user_id: uuid.UUID, token: str, platform: str) -> DeviceToken:
        stmt = select(DeviceToken).where(
            DeviceToken.user_id == user_id,
            DeviceToken.token == token,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.platform = platform
            return existing
        dt = DeviceToken(user_id=user_id, token=token, platform=platform)
        self.session.add(dt)
        await self.session.flush()
        return dt
