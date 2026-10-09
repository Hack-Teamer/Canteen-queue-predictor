from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
import uuid
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.redis import RedisChannels, RedisKeys
from app.core.websocket_manager import ws_manager
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.user import User
from app.repositories.menu_repo import MenuRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.order import (
    Explanation,
    OrderCreate,
    OrderCreateResponse,
    OrderItemRead,
    OrderRead,
    WaitRange,
)
from app.services.notification_service import NotificationService
from app.services.prediction_service import PredictionService
from app.services.queue_service import QueueService


class OrderService:
    ALLOWED_TRANSITIONS = {
        OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
        OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
        OrderStatus.PREPARING: [OrderStatus.READY],
        OrderStatus.READY: [OrderStatus.COLLECTED],
        OrderStatus.COLLECTED: [],
        OrderStatus.CANCELLED: [],
    }

    def __init__(
        self,
        session: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.order_repo = OrderRepository(session)
        self.menu_repo = MenuRepository(session)
        self.prediction_service = PredictionService(session, redis)
        self.queue_service = QueueService(session, redis)
        self.notification_service = NotificationService(session)

    async def _get_next_token_number(self) -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.redis:
            try:
                key = RedisKeys.token_counter(today_str)
                token_num = await self.redis.incr(key)
                if token_num == 1:
                    await self.redis.expire(key, 86400 * 2)
                return token_num
            except Exception:
                pass
        # Fallback to DB
        max_today = await self.order_repo.get_max_token_today()
        return max_today + 1

    async def create_order(
        self,
        user: User,
        order_in: OrderCreate,
        idempotency_key: Optional[str] = None,
    ) -> OrderCreateResponse:
        # Check idempotency
        if idempotency_key and self.redis:
            cached_resp = await self.redis.get(RedisKeys.idempotency_key(idempotency_key))
            if cached_resp:
                return OrderCreateResponse.model_validate_json(cached_resp)

        # 1. Validate items
        item_ids = [item.menu_item_id for item in order_in.items]
        menu_items = await self.menu_repo.get_items_by_ids(item_ids)
        menu_item_map = {item.id: item for item in menu_items}

        if len(menu_items) != len(set(item_ids)):
            raise NotFoundError("One or more menu items not found", code="ITEM_NOT_FOUND")

        for item in menu_items:
            if not item.is_available:
                raise BadRequestError(f"Item '{item.name}' is currently unavailable", code="ITEM_UNAVAILABLE")

        # Split items by station & calculate prep
        items_by_station: Dict[str, float] = {}
        total_items_count = 0
        order_items: List[OrderItem] = []

        for req_item in order_in.items:
            m_item = menu_item_map[req_item.menu_item_id]
            st_name = m_item.station.name.lower() if m_item.station else str(m_item.station_id)
            prep_load = m_item.prep_minutes * req_item.quantity
            items_by_station[st_name] = items_by_station.get(st_name, 0.0) + prep_load
            total_items_count += req_item.quantity

            order_items.append(
                OrderItem(
                    menu_item_id=m_item.id,
                    quantity=req_item.quantity,
                    station_id=m_item.station_id,
                )
            )

        # 2. Issue atomic daily token & create order
        token_number = await self._get_next_token_number()
        now = datetime.now(timezone.utc)

        order = Order(
            user_id=user.id,
            token_number=token_number,
            status=OrderStatus.PLACED,
            placed_at=now,
            next_class_at=order_in.next_class_at,
            items=order_items,
        )
        created_order = await self.order_repo.create_order(order)
        await self.order_repo.add_queue_event(
            order_id=created_order.id,
            from_status=None,
            to_status=OrderStatus.PLACED.value,
            actor_id=user.id,
        )

        # 3. Add to live queue in Redis
        await self.queue_service.add_to_queue(
            order_id=str(created_order.id),
            placed_time=now.timestamp(),
            items_by_station=items_by_station,
        )

        # 4. Compute prediction & store
        wait_range, features, explanation = await self.prediction_service.predict_wait_time(
            order_items_by_station=items_by_station,
            total_items=total_items_count,
            order_id=created_order.id,
            placed_at=now,
        )

        # 5. Broadcast to Kitchen & Queue WebSockets
        kitchen_msg = {
            "type": "order_updated",
            "order_id": str(created_order.id),
            "token_number": token_number,
            "status": OrderStatus.PLACED.value,
            "items": [
                {"name": menu_item_map[i.menu_item_id].name, "quantity": i.quantity}
                for i in order_items
            ],
            "eta": {"low": wait_range.low, "median": wait_range.median, "high": wait_range.high},
        }
        await ws_manager.broadcast_kitchen(kitchen_msg)
        await ws_manager.broadcast_queue({
            "type": "queue_summary",
            "active_orders": (await self.queue_service.get_queue_summary()).active_orders,
            "station_loads": explanation.station_loads,
        })

        response = OrderCreateResponse(
            order_id=created_order.id,
            token_number=token_number,
            status=OrderStatus.PLACED,
            wait=wait_range,
            explanation=explanation,
        )

        # Cache idempotency
        if idempotency_key and self.redis:
            await self.redis.set(
                RedisKeys.idempotency_key(idempotency_key),
                response.model_dump_json(),
                ex=86400,
            )

        return response

    async def update_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")

        # Validate transition
        allowed = self.ALLOWED_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise ConflictError(
                f"Invalid status transition from '{order.status.value}' to '{new_status.value}'",
                code="INVALID_STATUS_TRANSITION",
            )

        old_status = order.status
        order.status = new_status
        now = datetime.now(timezone.utc)

        # Compute items prep load
        items_by_station: Dict[str, float] = {}
        for item in order.items:
            st_name = item.station.name.lower() if item.station else str(item.station_id)
            prep = item.menu_item.prep_minutes if item.menu_item else 2.0
            items_by_station[st_name] = items_by_station.get(st_name, 0.0) + prep * item.quantity

        if new_status == OrderStatus.ACCEPTED:
            order.accepted_at = now
        elif new_status == OrderStatus.PREPARING:
            pass
        elif new_status == OrderStatus.READY:
            order.ready_at = now
            # Compute actual wait
            actual_wait = (now - order.placed_at).total_seconds() / 60.0
            await self.prediction_service.log_actual_wait(order.id, actual_wait)
            # Remove load from queue
            await self.queue_service.remove_from_queue(str(order.id), items_by_station)
            # Notify student
            await self.notification_service.notify_user(
                user_id=order.user_id,
                title="Order Ready for Pickup!",
                body=f"Your token #{order.token_number} is ready at the counter.",
                type="order_ready",
                order_id=order.id,
            )
            # Real-time ready event
            await ws_manager.broadcast_queue({
                "type": "order_ready",
                "order_id": str(order.id),
                "token_number": order.token_number,
            })
        elif new_status == OrderStatus.COLLECTED:
            order.collected_at = now
        elif new_status == OrderStatus.CANCELLED:
            # If cancelled before ready, remove from queue
            if old_status in [OrderStatus.PLACED, OrderStatus.ACCEPTED]:
                await self.queue_service.remove_from_queue(str(order.id), items_by_station)
            await self.notification_service.notify_user(
                user_id=order.user_id,
                title="Order Cancelled",
                body=f"Your order #{order.token_number} has been cancelled.",
                type="order_cancelled",
                order_id=order.id,
            )

        await self.order_repo.add_queue_event(
            order_id=order.id,
            from_status=old_status.value,
            to_status=new_status.value,
            actor_id=actor_id,
        )

        # Broadcast update
        update_payload = {
            "type": "order_updated",
            "order_id": str(order.id),
            "status": new_status.value,
            "token_number": order.token_number,
        }
        await ws_manager.broadcast_kitchen(update_payload)
        await ws_manager.send_to_user(str(order.user_id), update_payload)

        # Recompute queue summary
        summary = await self.queue_service.get_queue_summary()
        await ws_manager.broadcast_queue({
            "type": "queue_summary",
            "active_orders": summary.active_orders,
            "station_loads": summary.station_loads,
        })

        return order

    async def get_order_by_id(self, order_id: uuid.UUID) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")
        return order

    async def get_user_orders(self, user_id: uuid.UUID) -> List[Order]:
        return await self.order_repo.get_orders_by_user(user_id)

    async def get_kitchen_orders(
        self,
        station_id: Optional[uuid.UUID] = None,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        return await self.order_repo.get_kitchen_orders(station_id, status)
