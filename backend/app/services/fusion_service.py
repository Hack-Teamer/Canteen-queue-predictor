from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisKeys
from app.models.station import Station
from app.repositories.crowd_repo import CrowdRepository
from app.repositories.menu_repo import MenuRepository
from app.repositories.order_repo import OrderRepository


class FusionService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.crowd_repo = CrowdRepository(session)
        self.order_repo = OrderRepository(session)
        self.menu_repo = MenuRepository(session)

    async def get_camera_count(self) -> Optional[float]:
        # 1. Try Redis latest
        if self.redis:
            val = await self.redis.get(RedisKeys.CROWD_LATEST)
            if val is not None:
                try:
                    return float(val)
                except ValueError:
                    pass

        # 2. Fallback to DB latest snapshot
        snapshot = await self.crowd_repo.get_latest_snapshot()
        if snapshot:
            now = datetime.now(timezone.utc)
            snap_time = snapshot.captured_at
            if snap_time.tzinfo is None:
                snap_time = snap_time.replace(tzinfo=timezone.utc)
            age = (now - snap_time).total_seconds()
            if age <= settings.CROWD_STALE_SECONDS:
                return float(snapshot.people_count)

        return None

    async def compute_fusion(
        self,
        current_dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if current_dt is None:
            current_dt = datetime.now(timezone.utc)

        camera_count = await self.get_camera_count()
        camera_available = camera_count is not None
        people_in_line = int(round(camera_count)) if camera_count is not None else 0

        # Query active orders (placed, accepted, preparing)
        active_orders = await self.order_repo.get_active_orders()
        online_in_line = len(active_orders)

        # Walk-in calculation
        if camera_available:
            estimated_walk_ins = max(0, people_in_line - online_in_line)
        else:
            estimated_walk_ins = 0

        # Stations info
        stations: List[Station] = await self.menu_repo.list_stations(active_only=True)
        station_cooks = {s.name.lower(): max(1, s.active_cooks) for s in stations}
        station_names = {str(s.id): s.name for s in stations}

        # Calculate known pending load per station from active orders
        known_prep_per_station: Dict[str, float] = {s.name.lower(): 0.0 for s in stations}
        pending_items_per_station: Dict[str, int] = {s.name.lower(): 0 for s in stations}

        for order in active_orders:
            for item in order.items:
                st_name = item.station.name.lower() if item.station else ""
                if not st_name and str(item.station_id) in station_names:
                    st_name = station_names[str(item.station_id)].lower()
                if not st_name:
                    continue
                prep = item.menu_item.prep_minutes if item.menu_item else 2.0
                known_prep_per_station[st_name] = (
                    known_prep_per_station.get(st_name, 0.0) + prep * item.quantity
                )
                pending_items_per_station[st_name] = (
                    pending_items_per_station.get(st_name, 0) + item.quantity
                )

        station_loads: Dict[str, float] = {}
        hour = current_dt.hour
        # Default demands
        default_demands = {
            "tea counter": settings.DEFAULT_STATION_DEMAND.get("tea", 0.45),
            "tea": settings.DEFAULT_STATION_DEMAND.get("tea", 0.45),
            "tawa": settings.DEFAULT_STATION_DEMAND.get("tawa", 0.35),
            "fryer": settings.DEFAULT_STATION_DEMAND.get("fryer", 0.20),
        }

        for s in stations:
            s_name = s.name.lower()
            cooks = station_cooks.get(s_name, 1)
            known_load = known_prep_per_station.get(s_name, 0.0) / cooks

            # Station demand weight
            demand_weight = default_demands.get(s_name, 0.3)
            walkin_load = estimated_walk_ins * demand_weight * 2.5 / cooks

            total_load = round(known_load + walkin_load, 2)
            station_loads[s_name] = total_load

            # Also sync load to Redis if redis is active
            if self.redis:
                await self.redis.set(RedisKeys.load_station(str(s.id)), str(total_load))

        # Find busiest station
        busiest_station = ""
        max_load = -1.0
        for s_name, load in station_loads.items():
            if load > max_load:
                max_load = load
                busiest_station = s_name

        return {
            "camera_available": camera_available,
            "people_in_line": people_in_line if camera_available else None,
            "online_in_line": online_in_line,
            "estimated_walk_ins": estimated_walk_ins,
            "station_loads": station_loads,
            "known_prep_per_station": known_prep_per_station,
            "pending_items_per_station": pending_items_per_station,
            "station_cooks": station_cooks,
            "busiest_station": busiest_station,
        }
