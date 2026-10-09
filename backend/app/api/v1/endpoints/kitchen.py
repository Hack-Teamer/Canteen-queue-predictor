from typing import List, Optional
import uuid
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_redis, require_role
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.kitchen import KitchenLoadResponse, KitchenOrderRead
from app.schemas.order import OrderItemRead, OrderStatusUpdate
from app.services.fusion_service import FusionService
from app.services.order_service import OrderService

router = APIRouter()


@router.get(
    "/orders",
    response_model=List[KitchenOrderRead],
    dependencies=[Depends(require_role(UserRole.KITCHEN, UserRole.ADMIN))],
)
async def list_kitchen_orders(
    station_id: Optional[uuid.UUID] = None,
    status: Optional[OrderStatus] = None,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = OrderService(session, redis)
    orders = await service.get_kitchen_orders(station_id, status)

    result = []
    for o in orders:
        items_read = [
            OrderItemRead(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                station_id=item.station_id,
                item_name=item.menu_item.name if item.menu_item else None,
                price=item.menu_item.price if item.menu_item else None,
            )
            for item in o.items
            if station_id is None or item.station_id == station_id
        ]
        latest_pred = o.predictions[-1] if o.predictions else None
        est_wait = int(latest_pred.pred_median) if latest_pred else None

        result.append(
            KitchenOrderRead(
                order_id=o.id,
                token_number=o.token_number,
                status=o.status,
                placed_at=o.placed_at,
                accepted_at=o.accepted_at,
                ready_at=o.ready_at,
                items=items_read,
                student_name=o.user.name if o.user else None,
                next_class_at=o.next_class_at,
                estimated_wait_minutes=est_wait,
            )
        )
    return result


@router.patch(
    "/orders/{order_id}/status",
    response_model=KitchenOrderRead,
    dependencies=[Depends(require_role(UserRole.KITCHEN, UserRole.ADMIN))],
)
async def update_kitchen_order_status(
    order_id: uuid.UUID,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(require_role(UserRole.KITCHEN, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = OrderService(session, redis)
    updated_order = await service.update_status(
        order_id, status_update.status, actor_id=current_user.id
    )

    items_read = [
        OrderItemRead(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            station_id=item.station_id,
            item_name=item.menu_item.name if item.menu_item else None,
            price=item.menu_item.price if item.menu_item else None,
        )
        for item in updated_order.items
    ]
    latest_pred = updated_order.predictions[-1] if updated_order.predictions else None

    return KitchenOrderRead(
        order_id=updated_order.id,
        token_number=updated_order.token_number,
        status=updated_order.status,
        placed_at=updated_order.placed_at,
        accepted_at=updated_order.accepted_at,
        ready_at=updated_order.ready_at,
        items=items_read,
        student_name=updated_order.user.name if updated_order.user else None,
        next_class_at=updated_order.next_class_at,
        estimated_wait_minutes=int(latest_pred.pred_median) if latest_pred else None,
    )


@router.get(
    "/load",
    response_model=KitchenLoadResponse,
    dependencies=[Depends(require_role(UserRole.KITCHEN, UserRole.ADMIN))],
)
async def get_kitchen_load(
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    fusion_service = FusionService(session, redis)
    info = await fusion_service.compute_fusion()

    breakdown = {}
    for st_name, load in info["station_loads"].items():
        breakdown[st_name] = {
            "total_load": load,
            "pending_items": float(info["pending_items_per_station"].get(st_name, 0)),
            "cooks": float(info["station_cooks"].get(st_name, 1)),
        }

    return KitchenLoadResponse(
        total_active_orders=info["online_in_line"],
        station_loads=info["station_loads"],
        station_breakdown=breakdown,
    )
