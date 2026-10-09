import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.menu_item import MenuItem
from app.models.station import Station


class MenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Station operations
    async def get_station_by_id(self, station_id: uuid.UUID) -> Optional[Station]:
        stmt = select(Station).where(Station.id == station_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_stations(self, active_only: bool = True) -> List[Station]:
        stmt = select(Station)
        if active_only:
            stmt = stmt.where(Station.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_station_cooks(self, station_id: uuid.UUID, active_cooks: int) -> Optional[Station]:
        station = await self.get_station_by_id(station_id)
        if station:
            station.active_cooks = active_cooks
            await self.session.flush()
        return station

    # Menu item operations
    async def get_menu_item_by_id(self, item_id: uuid.UUID) -> Optional[MenuItem]:
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.station))
            .where(MenuItem.id == item_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_menu_items(self, available_only: bool = True) -> List[MenuItem]:
        stmt = select(MenuItem).options(selectinload(MenuItem.station))
        if available_only:
            stmt = stmt.where(MenuItem.is_available.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_items_by_ids(self, item_ids: List[uuid.UUID]) -> List[MenuItem]:
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.station))
            .where(MenuItem.id.in_(item_ids))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_menu_item(self, item: MenuItem) -> MenuItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_menu_item(self, item: MenuItem) -> MenuItem:
        await self.session.flush()
        return item

    async def delete_menu_item(self, item: MenuItem) -> None:
        await self.session.delete(item)
        await self.session.flush()
