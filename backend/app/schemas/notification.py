import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DeviceTokenCreate(BaseModel):
    token: str
    platform: str = "web"


class DeviceTokenRead(BaseModel):
    id: uuid.UUID
    token: str
    platform: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    type: str
    title: str
    body: str
    sent_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
