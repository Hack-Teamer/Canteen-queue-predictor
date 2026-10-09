import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StationBase(BaseModel):
    name: str
    active_cooks: int = Field(default=1, ge=1)
    is_active: bool = True


class StationCreate(StationBase):
    pass


class StationUpdate(BaseModel):
    name: Optional[str] = None
    active_cooks: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class StationRead(StationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuItemBase(BaseModel):
    name: str
    price: float = Field(ge=0.0)
    station_id: uuid.UUID
    prep_minutes: float = Field(default=2.0, gt=0.0)
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    station_id: Optional[uuid.UUID] = None
    prep_minutes: Optional[float] = Field(default=None, gt=0.0)
    is_available: Optional[bool] = None


class MenuItemRead(MenuItemBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    station: Optional[StationRead] = None

    model_config = ConfigDict(from_attributes=True)
