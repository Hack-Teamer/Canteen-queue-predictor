from typing import Dict, Optional
from pydantic import BaseModel


class StationLoadInfo(BaseModel):
    station_id: str
    station_name: str
    load_minutes: float
    active_cooks: int
    pending_items: int


class QueueSummaryResponse(BaseModel):
    active_orders: int
    station_loads: Dict[str, float]
    crowd_count: Optional[int] = None
    crowd_level: str = "low"  # low, medium, high
    rush_warning: bool = False
    minutes_to_next_bell: Optional[int] = None
