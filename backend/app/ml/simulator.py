import math
import random
from typing import Any, Dict, List
import numpy as np
import pandas as pd
import simpy

from app.ml.features import FEATURE_COLUMNS, build_feature_dict


class CanteenSimulator:
    def __init__(
        self,
        seed: int = 42,
        target_orders: int = 5000,
        walk_in_ratio: float = 0.35,
    ) -> None:
        self.seed = seed
        self.target_orders = target_orders
        self.walk_in_ratio = walk_in_ratio
        random.seed(seed)
        np.random.seed(seed)

        # Station configurations: (default_cooks, base_prep_minutes)
        self.station_configs = {
            "tea": {"cooks": 2, "base_prep": 1.8},
            "tawa": {"cooks": 2, "base_prep": 4.5},
            "fryer": {"cooks": 1, "base_prep": 3.0},
        }

        # Timetable bell minutes within an 8-hour day (480 minutes: 0 = 9:00 AM)
        # 10:30 AM = minute 90 (break)
        # 12:30 PM = minute 210 (break)
        # 03:00 PM = minute 360 (break)
        self.bell_minutes = [
            (90, True),   # 10:30 AM Morning Tea
            (120, False), # 11:00 AM Period
            (210, True),  # 12:30 PM Lunch
            (270, False), # 01:30 PM Period
            (360, True),  # 03:00 PM Snack Break
        ]

    def _get_arrival_interval(self, current_day_minute: float) -> float:
        # Base inter-arrival time in minutes (mean ~2.5 mins in normal times)
        base_mean = 2.5

        # Check if within 10-15 minutes after any bell
        spike_multiplier = 1.0
        for bell_min, is_break in self.bell_minutes:
            diff = current_day_minute - bell_min
            if 0 <= diff <= 12:
                spike_multiplier = 0.3 if is_break else 0.5  # arrivals much more frequent
                break

        interval = np.random.exponential(scale=base_mean * spike_multiplier)
        return max(0.2, interval)

    def _sample_prep_time(self, base_prep: float) -> float:
        # Lognormal distribution around base prep time
        mu = math.log(base_prep)
        sigma = 0.25
        return float(np.random.lognormal(mean=mu, sigma=sigma))

    def run(self) -> pd.DataFrame:
        env = simpy.Environment()

        # SimPy resources for stations
        resources = {
            name: simpy.Resource(env, capacity=cfg["cooks"])
            for name, cfg in self.station_configs.items()
        }

        # Tracking state
        active_walk_ins: List[float] = []
        station_queue_lengths = {st: 0 for st in self.station_configs}
        station_workload_mins = {st: 0.0 for st in self.station_configs}

        recorded_rows: List[Dict[str, Any]] = []

        def order_process(order_id: int, is_walk_in: bool, day: int, day_minute: float):
            arrival_time = env.now
            # Generate items: 1 to 4 items across stations
            num_items = random.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.10])[0]
            items: List[Dict[str, Any]] = []

            for _ in range(num_items):
                st_name = random.choices(
                    ["tea", "tawa", "fryer"],
                    weights=[0.50, 0.32, 0.18],
                )[0]
                prep_time = self._sample_prep_time(self.station_configs[st_name]["base_prep"])
                items.append({"station": st_name, "prep_time": prep_time})

            # Calculate feature state before queuing
            minutes_since_bell = 120
            is_break_active = False
            for bell_min, is_brk in reversed(self.bell_minutes):
                if day_minute >= bell_min:
                    diff = int(day_minute - bell_min)
                    minutes_since_bell = diff
                    is_break_active = is_brk and (diff <= 30)
                    break

            people_in_zone = len(active_walk_ins) + sum(station_queue_lengths.values())
            # Camera noise
            measured_people = max(0, people_in_zone + random.randint(-1, 2))
            estimated_walk_ins = max(0, measured_people - sum(station_queue_lengths.values()))

            hour_of_day = int(9 + (day_minute // 60)) % 24
            active_cooks = {st: cfg["cooks"] for st, cfg in self.station_configs.items()}

            feature_dict = build_feature_dict(
                items_ahead_per_station={
                    f"items_ahead_{st}": station_queue_lengths[st]
                    for st in self.station_configs
                },
                minutes_ahead_per_station={
                    f"minutes_ahead_{st}": station_workload_mins[st]
                    for st in self.station_configs
                },
                items_in_this_order=num_items,
                people_in_zone=measured_people,
                estimated_walk_ins=estimated_walk_ins,
                hour=hour_of_day,
                day_of_week=day % 5,
                minutes_since_last_bell=minutes_since_bell,
                is_break=is_break_active,
                active_cooks_per_station=active_cooks,
            )

            if is_walk_in:
                active_walk_ins.append(arrival_time)

            # Update queues
            for item in items:
                st = item["station"]
                station_queue_lengths[st] += 1
                station_workload_mins[st] += item["prep_time"]

            # Process items on each station concurrently
            station_item_groups: Dict[str, List[float]] = {}
            for item in items:
                station_item_groups.setdefault(item["station"], []).append(item["prep_time"])

            def process_at_station(st: str, preps: List[float]):
                for p in preps:
                    req = resources[st].request()
                    yield req
                    yield env.timeout(p)
                    resources[st].release(req)
                    station_queue_lengths[st] = max(0, station_queue_lengths[st] - 1)
                    station_workload_mins[st] = max(0.0, station_workload_mins[st] - p)

            yield simpy.AllOf(
                env,
                [env.process(process_at_station(st, preps)) for st, preps in station_item_groups.items()],
            )

            finish_time = env.now
            actual_wait = finish_time - arrival_time

            if is_walk_in and arrival_time in active_walk_ins:
                active_walk_ins.remove(arrival_time)

            if not is_walk_in and len(recorded_rows) < self.target_orders:
                row = {**feature_dict, "actual_wait": round(actual_wait, 2)}
                recorded_rows.append(row)

        def order_generator():
            order_id = 0
            day = 0
            while len(recorded_rows) < self.target_orders:
                # 8-hour day = 480 minutes
                day_minute = env.now % 480
                is_walk_in = random.random() < self.walk_in_ratio

                env.process(order_process(order_id, is_walk_in, day, day_minute))
                order_id += 1

                interval = self._get_arrival_interval(day_minute)
                yield env.timeout(interval)

                if (env.now // 480) > day:
                    day += 1

        env.process(order_generator())
        env.run(until=simpy.events.AnyOf(env, [env.timeout(100000)]))

        df = pd.DataFrame(recorded_rows)
        return df


def generate_canteen_dataset(
    target_orders: int = 5000, seed: int = 42
) -> pd.DataFrame:
    simulator = CanteenSimulator(seed=seed, target_orders=target_orders)
    return simulator.run()
