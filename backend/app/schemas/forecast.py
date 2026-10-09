from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ForecastSlot(BaseModel):
    slot_time: datetime
    predicted_median: int
    low: int
    high: int
    rush_factor: float = 1.0


class ForecastResponse(BaseModel):
    generated_at: datetime
    slots: List[ForecastSlot]
    best_slot: ForecastSlot
    recommendation: str


class LeaveTimeResponse(BaseModel):
    next_class_at: datetime
    current_time: datetime
    predicted_wait_minutes: int
    buffer_minutes: int = 3
    leave_now_time: datetime
    can_make_it: bool
    advice: str
