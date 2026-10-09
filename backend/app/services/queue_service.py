from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisChannels, RedisKeys
from app.models.station import Station
from app.repositories.menu_repo import MenuRepository
from app.schemas.queue import QueueSummaryResponse
from app.services.fusion_service import FusionService
from app.services.timetable_service import TimetableService


class QueueService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.menu_repo = MenuRepository(session)
        self.fusion_service = FusionService(session, redis)
        self.timetable_service = TimetableService(session)

    async def add_to_queue(self, order_id: str, placed_time: float, items_by_station: Dict[str, float]) -> None:
        if not self.redis:
            return
        # Add to sorted set of active orders
        await self.redis.zadd(RedisKeys.QUEUE_ACTIVE, {order_id: placed_time})
        for st_id, prep_load in items_by_station.items():
            await self.redis.rpush(RedisKeys.queue_station(st_id), json.dumps({"order_id": order_id, "load": prep_load}))
            # Increment station load
            await self.redis.incrbyfloat(RedisKeys.load_station(st_id), prep_load)

    async def remove_from_queue(self, order_id: str, items_by_station: Dict[str, float]) -> None:
        if not self.redis:
            return
        await self.redis.zrem(RedisKeys.QUEUE_ACTIVE, order_id)
        for st_id, prep_load in items_by_station.items():
            # Decrement station load ensuring not below 0
            curr = await self.redis.get(RedisKeys.load_station(st_id))
            if curr:
                new_load = max(0.0, float(curr) - prep_load)
                await self.redis.set(RedisKeys.load_station(st_id), str(round(new_load, 2)))

    async def get_queue_summary(self) -> QueueSummaryResponse:
        now = datetime.now(timezone.utc)
        fusion_info = await self.fusion_service.compute_fusion(now)
        active_count = fusion_info["online_in_line"]
        station_loads = fusion_info["station_loads"]
        crowd_count = fusion_info["people_in_line"]

        # Timetable
        _, is_break, minutes_to_bell = await self.timetable_service.get_timetable_context(now)
        rush_warning = (minutes_to_bell is not None and minutes_to_bell <= 10) or is_break

        # Crowd level categorization
        if crowd_count is None:
            crowd_level = "normal"
        elif crowd_count < 10:
            crowd_level = "low"
        elif crowd_count < 25:
            crowd_level = "medium"
        else:
            crowd_level = "high"

        return QueueSummaryResponse(
            active_orders=active_count,
            station_loads=station_loads,
            crowd_count=crowd_count,
            crowd_level=crowd_level,
            rush_warning=rush_warning,
            minutes_to_next_bell=minutes_to_bell,
        )
