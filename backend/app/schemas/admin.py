from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class AdminSummary(BaseModel):
    total_orders_today: int
    active_orders_now: int
    completed_orders_today: int
    avg_wait_time_minutes: float
    total_revenue_today: float
    current_crowd_count: Optional[int]


class PeakHourStat(BaseModel):
    hour: int
    order_count: int
    avg_wait_minutes: float


class StationStat(BaseModel):
    station_id: uuid.UUID
    station_name: str
    active_cooks: int
    items_processed_today: int
    avg_prep_time_minutes: float
    current_load_minutes: float


class PopularItemStat(BaseModel):
    menu_item_id: uuid.UUID
    item_name: str
    order_count: int
    total_revenue: float


class AccuracyMetrics(BaseModel):
    sample_count: int
    mae: float
    rmse: float
    coverage_80_percent: float  # Percentage of actual waits falling between q10 and q90
    baseline_mae: float
    improvement_vs_baseline_percent: float


class ModelInfo(BaseModel):
    current_version: str
    promoted_at: Optional[datetime]
    metrics: Dict[str, Any]
    feature_importance: Dict[str, float]
    available_versions: List[str]

    model_config = ConfigDict(protected_namespaces=())


class RetrainRequest(BaseModel):
    min_rows: Optional[int] = 500
    force: bool = False


class RetrainResponse(BaseModel):
    status: str
    message: str
    new_version: Optional[str] = None
    promoted: bool = False
    evaluation: Optional[Dict[str, Any]] = None


class RollbackResponse(BaseModel):
    status: str
    message: str
    active_version: str
