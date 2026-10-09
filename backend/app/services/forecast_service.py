from datetime import datetime, timedelta, timezone
import json
from typing import List, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisKeys
from app.schemas.forecast import ForecastResponse, ForecastSlot, LeaveTimeResponse
from app.services.prediction_service import PredictionService
from app.services.timetable_service import TimetableService


class ForecastService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.prediction_service = PredictionService(session, redis)
        self.timetable_service = TimetableService(session)

    async def get_next_30_minutes_forecast(self, force_refresh: bool = False) -> ForecastResponse:
        # Check Redis cache
        if self.redis and not force_refresh:
            cached = await self.redis.get(RedisKeys.FORECAST_NEXT30)
            if cached:
                try:
                    return ForecastResponse.model_validate_json(cached)
                except Exception:
                    pass

        now = datetime.now(timezone.utc)
        slots: List[ForecastSlot] = []

        # Average reference order: 1 tea (2 mins) + 1 snack (3 mins)
        ref_order = {"tea counter": 2.0, "tawa": 3.0}

        for offset in [0, 5, 10, 15, 20, 25]:
            slot_time = now + timedelta(minutes=offset)
            rush_factor = await self.timetable_service.get_rush_factor(slot_time)

            wait_range, _, _ = await self.prediction_service.predict_wait_time(
                order_items_by_station=ref_order,
                total_items=2,
                order_id=None,
                placed_at=slot_time,
            )

            # Adjust wait by projected rush factor
            adj_median = max(1, round(wait_range.median * rush_factor))
            adj_low = max(1, round(wait_range.low * rush_factor))
            adj_high = max(adj_median, round(wait_range.high * rush_factor))

            slots.append(
                ForecastSlot(
                    slot_time=slot_time,
                    predicted_median=adj_median,
                    low=adj_low,
                    high=adj_high,
                    rush_factor=round(rush_factor, 2),
                )
            )

        best_slot = min(slots, key=lambda s: s.predicted_median)
        diff_mins = int((best_slot.slot_time - now).total_seconds() / 60)
        if diff_mins == 0:
            recommendation = "Now is the optimal time to place your order!"
        else:
            recommendation = f"Ordering in {diff_mins} minutes has the lowest expected wait time ({best_slot.predicted_median} mins)."

        forecast = ForecastResponse(
            generated_at=now,
            slots=slots,
            best_slot=best_slot,
            recommendation=recommendation,
        )

        # Cache in Redis with 90s TTL
        if self.redis:
            await self.redis.set(
                RedisKeys.FORECAST_NEXT30,
                forecast.model_dump_json(),
                ex=90,
            )

        return forecast

    async def calculate_leave_time(self, next_class_at: datetime) -> LeaveTimeResponse:
        now = datetime.now(timezone.utc)
        if next_class_at.tzinfo is None:
            next_class_at = next_class_at.replace(tzinfo=timezone.utc)

        # Average reference order
        ref_order = {"tea counter": 2.0, "tawa": 3.0}
        wait_range, _, _ = await self.prediction_service.predict_wait_time(
            order_items_by_station=ref_order,
            total_items=2,
            order_id=None,
            placed_at=now,
        )

        buffer_minutes = 3
        total_time_needed = wait_range.median + buffer_minutes
        leave_now_time = next_class_at - timedelta(minutes=total_time_needed)

        can_make_it = leave_now_time >= now
        if can_make_it:
            mins_left = int((leave_now_time - now).total_seconds() / 60)
            advice = f"You have {mins_left} minutes before you must place your order to make it to class on time."
        else:
            advice = "Wait time exceeds available time before class. We recommend ordering after class."

        return LeaveTimeResponse(
            next_class_at=next_class_at,
            current_time=now,
            predicted_wait_minutes=wait_range.median,
            buffer_minutes=buffer_minutes,
            leave_now_time=leave_now_time,
            can_make_it=can_make_it,
            advice=advice,
        )
