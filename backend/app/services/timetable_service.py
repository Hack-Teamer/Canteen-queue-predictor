from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable_slot import TimetableSlot
from app.repositories.analytics_repo import AnalyticsRepository


class TimetableService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnalyticsRepository(session)

    async def get_slots_for_day(self, day_of_week: int) -> List[TimetableSlot]:
        return await self.repo.get_timetable_slots(day_of_week)

    async def get_timetable_context(
        self, current_dt: Optional[datetime] = None
    ) -> Tuple[int, bool, Optional[int]]:
        """
        Returns:
            minutes_since_last_bell: int (minutes since previous bell today, default 60 if none)
            is_break: bool (True if current time is within break window or active break slot)
            minutes_to_next_bell: Optional[int] (minutes until next bell today)
        """
        if current_dt is None:
            current_dt = datetime.now(timezone.utc)

        day_of_week = current_dt.weekday()
        current_time = current_dt.time()

        slots = await self.get_slots_for_day(day_of_week)
        if not slots:
            return 60, False, None

        current_minutes = current_time.hour * 60 + current_time.minute

        past_slots = []
        future_slots = []

        for slot in slots:
            slot_minutes = slot.bell_time.hour * 60 + slot.bell_time.minute
            if slot_minutes <= current_minutes:
                past_slots.append((slot, current_minutes - slot_minutes))
            else:
                future_slots.append((slot, slot_minutes - current_minutes))

        # Determine minutes_since_last_bell and is_break
        if past_slots:
            last_slot, diff = past_slots[-1]
            minutes_since_last_bell = diff
            # Break window lasts 30 minutes after a break bell
            is_break = last_slot.is_break and (diff <= 30)
        else:
            minutes_since_last_bell = 120
            is_break = False

        # Determine minutes_to_next_bell
        minutes_to_next_bell = future_slots[0][1] if future_slots else None

        return minutes_since_last_bell, is_break, minutes_to_next_bell

    async def get_rush_factor(self, dt: datetime) -> float:
        """
        Bell spikes: up to 10-15 minutes after bells, arrival rush increases significantly (1.5x - 2.5x).
        """
        minutes_since_last_bell, is_break, _ = await self.get_timetable_context(dt)
        if minutes_since_last_bell <= 15:
            # Peak rush just after the bell
            return 2.2 if is_break else 1.6
        elif minutes_since_last_bell <= 30 and is_break:
            return 1.4
        return 1.0
