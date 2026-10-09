import math
from typing import Dict, List
from app.schemas.order import WaitRange


class BaselineETAService:
    @staticmethod
    def calculate_eta(
        station_loads: Dict[str, float],
        own_items_by_station: Dict[str, float],
        station_cooks: Dict[str, int],
    ) -> WaitRange:
        """
        Baseline station-aware formula:
        wait = max over stations (station_load + own_prep_time_at_station)
        range = +/- 25% (low floor, high ceil, min 1)
        """
        station_waits: List[float] = []

        for station_name, own_prep in own_items_by_station.items():
            cooks = max(1, station_cooks.get(station_name, 1))
            current_station_load = station_loads.get(station_name, 0.0)
            station_prep = own_prep / cooks
            total_station_wait = current_station_load + station_prep
            station_waits.append(total_station_wait)

        if not station_waits:
            # Fallback if no station items
            base_wait = 5.0
        else:
            base_wait = max(station_waits)

        median_val = max(1, round(base_wait))
        low_val = max(1, math.floor(base_wait * 0.75))
        high_val = max(median_val, math.ceil(base_wait * 1.25))

        # Enforce consistency: low <= median <= high
        if low_val > median_val:
            low_val = median_val
        if high_val < median_val:
            high_val = median_val

        return WaitRange(
            low=int(low_val),
            median=int(median_val),
            high=int(high_val),
            source="baseline",
            model_version="baseline_v1",
        )
