from typing import List, Optional
import uuid
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import (
    get_current_user,
    get_db,
    get_redis,
    rate_limiter,
    require_role,
)
from app.core.exceptions import ForbiddenError
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import (
    OrderCreate,
    OrderCreateResponse,
    OrderItemRead,
    OrderRead,
    WaitRange,
)
from app.services.order_service import OrderService

router = APIRouter()


@router.post("", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    order_in: OrderCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    await rate_limiter(
        prefix="orders",
        limit=settings.RATE_LIMIT_ORDER_PER_MINUTE,
        identifier=str(current_user.id),
        redis=redis,
    )
    service = OrderService(session, redis)
    return await service.create_order(
        user=current_user,
        order_in=order_in,
        idempotency_key=idempotency_key,
    )


@router.get("/me", response_model=List[OrderRead])
async def get_my_orders(
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = OrderService(session, redis)
    orders = await service.get_user_orders(current_user.id)
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
        ]
        latest_pred = o.predictions[-1] if o.predictions else None
        wait_val = None
        if latest_pred:
            wait_val = WaitRange(
                low=int(latest_pred.pred_low),
                median=int(latest_pred.pred_median),
                high=int(latest_pred.pred_high),
                source=latest_pred.source.value if hasattr(latest_pred.source, "value") else str(latest_pred.source),
                model_version=latest_pred.model_version,
            )
        result.append(
            OrderRead(
                id=o.id,
                user_id=o.user_id,
                token_number=o.token_number,
                status=o.status,
                placed_at=o.placed_at,
                accepted_at=o.accepted_at,
                ready_at=o.ready_at,
                collected_at=o.collected_at,
                next_class_at=o.next_class_at,
                items=items_read,
                current_wait=wait_val,
            )
        )
    return result


@router.get("/{order_id}", response_model=OrderRead)
async def get_order_details(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = OrderService(session, redis)
    order = await service.get_order_by_id(order_id)
    if current_user.role == UserRole.STUDENT and order.user_id != current_user.id:
        raise ForbiddenError("You cannot view this order", code="FORBIDDEN_ORDER_ACCESS")

    items_read = [
        OrderItemRead(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            station_id=item.station_id,
            item_name=item.menu_item.name if item.menu_item else None,
            price=item.menu_item.price if item.menu_item else None,
        )
        for item in order.items
    ]
    latest_pred = order.predictions[-1] if order.predictions else None
    wait_val = None
    if latest_pred:
        wait_val = WaitRange(
            low=int(latest_pred.pred_low),
            median=int(latest_pred.pred_median),
            high=int(latest_pred.pred_high),
            source=latest_pred.source.value if hasattr(latest_pred.source, "value") else str(latest_pred.source),
            model_version=latest_pred.model_version,
        )

    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        token_number=order.token_number,
        status=order.status,
        placed_at=order.placed_at,
        accepted_at=order.accepted_at,
        ready_at=order.ready_at,
        collected_at=order.collected_at,
        next_class_at=order.next_class_at,
        items=items_read,
        current_wait=wait_val,
    )


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = OrderService(session, redis)
    order = await service.get_order_by_id(order_id)
    if current_user.role == UserRole.STUDENT and order.user_id != current_user.id:
        raise ForbiddenError("You cannot cancel this order", code="FORBIDDEN_ORDER_CANCEL")

    updated = await service.update_status(order_id, OrderStatus.CANCELLED, actor_id=current_user.id)
    items_read = [
        OrderItemRead(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            station_id=item.station_id,
            item_name=item.menu_item.name if item.menu_item else None,
            price=item.menu_item.price if item.menu_item else None,
        )
        for item in updated.items
    ]
    return OrderRead(
        id=updated.id,
        user_id=updated.user_id,
        token_number=updated.token_number,
        status=updated.status,
        placed_at=updated.placed_at,
        accepted_at=updated.accepted_at,
        ready_at=updated.ready_at,
        collected_at=updated.collected_at,
        next_class_at=updated.next_class_at,
        items=items_read,
    )
