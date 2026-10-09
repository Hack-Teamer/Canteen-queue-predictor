from datetime import datetime
from pydantic import BaseModel, Field


class VisionCountInput(BaseModel):
    people_count: int = Field(..., ge=0)
    zone_id: str = "canteen_queue_zone"
    captured_at: datetime


class VisionCountResponse(BaseModel):
    status: str = "success"
    raw_count: int
    smoothed_count: float
    captured_at: datetime
    zone_id: str
