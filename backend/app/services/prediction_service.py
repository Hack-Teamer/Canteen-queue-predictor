from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.ml.features import build_feature_dict
from app.ml.predictor import predictor
from app.models.prediction import Prediction, PredictionSource
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.order import Explanation, WaitRange
from app.services.baseline_eta_service import BaselineETAService
from app.services.fusion_service import FusionService
from app.services.timetable_service import TimetableService


class PredictionService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.prediction_repo = PredictionRepository(session)
        self.fusion_service = FusionService(session, redis)
        self.timetable_service = TimetableService(session)

    async def predict_wait_time(
        self,
        order_items_by_station: Dict[str, float],
        total_items: int,
        order_id: Optional[uuid.UUID] = None,
        placed_at: Optional[datetime] = None,
    ) -> Tuple[WaitRange, Dict[str, Any], Explanation]:
        if placed_at is None:
            placed_at = datetime.now(timezone.utc)

        # 1. Fusion state
        fusion_info = await self.fusion_service.compute_fusion(placed_at)
        station_loads = fusion_info["station_loads"]
        station_cooks = fusion_info["station_cooks"]
        estimated_walk_ins = fusion_info["estimated_walk_ins"]
        people_in_zone = fusion_info["people_in_line"] or 0
        busiest_station = fusion_info["busiest_station"]

        # 2. Timetable context
        minutes_since_bell, is_break, _ = await self.timetable_service.get_timetable_context(placed_at)

        # 3. Build features
        features = build_feature_dict(
            items_ahead_per_station=fusion_info["pending_items_per_station"],
            minutes_ahead_per_station=station_loads,
            items_in_this_order=total_items,
            people_in_zone=people_in_zone,
            estimated_walk_ins=estimated_walk_ins,
            hour=placed_at.hour,
            day_of_week=placed_at.weekday(),
            minutes_since_last_bell=minutes_since_bell,
            is_break=is_break,
            active_cooks_per_station=station_cooks,
        )

        # 4. Predict via ML model
        wait_range = predictor.predict(features)

        # 5. Fallback to baseline if ML unavailable
        if wait_range is None:
            wait_range = BaselineETAService.calculate_eta(
                station_loads=station_loads,
                own_items_by_station=order_items_by_station,
                station_cooks=station_cooks,
            )

        explanation = Explanation(
            estimated_walk_ins=estimated_walk_ins,
            busiest_station=busiest_station,
            station_loads=station_loads,
        )

        # 6. Store prediction row if order_id is present
        if order_id:
            db_pred = Prediction(
                order_id=order_id,
                model_version=wait_range.model_version,
                source=(
                    PredictionSource.ML
                    if wait_range.source == "ml"
                    else PredictionSource.BASELINE
                ),
                pred_low=wait_range.low,
                pred_median=wait_range.median,
                pred_high=wait_range.high,
                features=features,
            )
            await self.prediction_repo.create_prediction(db_pred)

        return wait_range, features, explanation

    async def log_actual_wait(self, order_id: uuid.UUID, actual_wait_minutes: float) -> None:
        await self.prediction_repo.update_actual_wait(order_id, actual_wait_minutes)
        logger.info(f"Recorded actual wait {actual_wait_minutes:.2f} mins for order {order_id}")
