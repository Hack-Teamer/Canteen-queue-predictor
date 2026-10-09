from typing import List
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.notification import DeviceTokenCreate, NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=List[NotificationRead])
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = NotificationService(session)
    return await service.get_user_notifications(current_user.id)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = NotificationService(session)
    notif = await service.mark_as_read(notification_id, current_user.id)
    if not notif:
        raise NotFoundError("Notification not found", code="NOTIFICATION_NOT_FOUND")
    return notif


@router.post("/device-token")
async def register_device_token(
    data: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = NotificationService(session)
    await service.register_device_token(
        user_id=current_user.id,
        token=data.token,
        platform=data.platform,
    )
    return {"status": "success", "message": "Device token registered"}
