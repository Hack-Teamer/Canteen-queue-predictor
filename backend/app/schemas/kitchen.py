import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models.order import OrderStatus
from app.schemas.order import OrderItemRead


class KitchenOrderRead(BaseModel):
    order_id: uuid.UUID
    token_number: int
    status: OrderStatus
    placed_at: datetime
    accepted_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    items: List[OrderItemRead]
    student_name: Optional[str] = None
    next_class_at: Optional[datetime] = None
    estimated_wait_minutes: Optional[int] = None


class KitchenLoadResponse(BaseModel):
    total_active_orders: int
    station_loads: Dict[str, float]
    station_breakdown: Dict[str, Dict[str, float]]
