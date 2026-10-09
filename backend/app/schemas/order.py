import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1)
    next_class_at: Optional[datetime] = None


class OrderItemRead(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    quantity: int
    station_id: uuid.UUID
    item_name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class WaitRange(BaseModel):
    low: int
    median: int
    high: int
    source: str = "baseline"  # "ml" or "baseline"
    model_version: str = "v1"

    model_config = ConfigDict(protected_namespaces=())


class Explanation(BaseModel):
    estimated_walk_ins: int = 0
    busiest_station: str = ""
    station_loads: Optional[Dict[str, float]] = None


class OrderCreateResponse(BaseModel):
    order_id: uuid.UUID
    token_number: int
    status: OrderStatus
    wait: WaitRange
    explanation: Explanation


class OrderRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    token_number: int
    status: OrderStatus
    placed_at: datetime
    accepted_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    next_class_at: Optional[datetime] = None
    items: List[OrderItemRead] = []
    current_wait: Optional[WaitRange] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
