from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.crowd_snapshot import CrowdSnapshot


class CrowdRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_snapshot(self, snapshot: CrowdSnapshot) -> CrowdSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest_snapshot(self, zone_id: str = "canteen_queue_zone") -> Optional[CrowdSnapshot]:
        stmt = (
            select(CrowdSnapshot)
            .where(CrowdSnapshot.zone_id == zone_id)
            .order_by(CrowdSnapshot.captured_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_snapshots(
        self, limit: int = 5, zone_id: str = "canteen_queue_zone"
    ) -> List[CrowdSnapshot]:
        stmt = (
            select(CrowdSnapshot)
            .where(CrowdSnapshot.zone_id == zone_id)
            .order_by(CrowdSnapshot.captured_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_snapshots_since(
        self, since: datetime, zone_id: str = "canteen_queue_zone"
    ) -> List[CrowdSnapshot]:
        stmt = (
            select(CrowdSnapshot)
            .where(
                CrowdSnapshot.zone_id == zone_id,
                CrowdSnapshot.captured_at >= since,
            )
            .order_by(CrowdSnapshot.captured_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
