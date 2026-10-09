from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.queue_event import QueueEvent


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.predictions),
                selectinload(Order.user),
            )
            .where(Order.id == order_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_orders_by_user(self, user_id: uuid.UUID, limit: int = 50) -> List[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.predictions),
            )
            .where(Order.user_id == user_id)
            .order_by(Order.placed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_orders(self) -> List[Order]:
        active_statuses = [
            OrderStatus.PLACED,
            OrderStatus.ACCEPTED,
            OrderStatus.PREPARING,
        ]
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.predictions),
            )
            .where(Order.status.in_(active_statuses))
            .order_by(Order.placed_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_kitchen_orders(
        self,
        station_id: Optional[uuid.UUID] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.predictions),
                selectinload(Order.user),
            )
        )
        if status:
            stmt = stmt.where(Order.status == status)
        else:
            # By default exclude collected and cancelled in active kitchen view
            stmt = stmt.where(Order.status.in_([
                OrderStatus.PLACED,
                OrderStatus.ACCEPTED,
                OrderStatus.PREPARING,
                OrderStatus.READY,
            ]))

        if station_id:
            stmt = stmt.join(Order.items).where(OrderItem.station_id == station_id)

        stmt = stmt.order_by(Order.placed_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_max_token_today(self) -> int:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(func.max(Order.token_number)).where(Order.placed_at >= today_start)
        result = await self.session.execute(stmt)
        max_val = result.scalar()
        return max_val if max_val is not None else 0

    async def create_order(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def add_queue_event(
        self,
        order_id: uuid.UUID,
        from_status: Optional[str],
        to_status: str,
        actor_id: Optional[uuid.UUID] = None,
    ) -> QueueEvent:
        event = QueueEvent(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event
