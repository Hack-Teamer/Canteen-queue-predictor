from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.core.exceptions import NotFoundError
from app.models.menu_item import MenuItem
from app.models.station import Station
from app.models.user import UserRole
from app.repositories.menu_repo import MenuRepository
from app.schemas.menu import (
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    StationCreate,
    StationRead,
    StationUpdate,
)

router = APIRouter()


@router.get("", response_model=List[MenuItemRead])
async def list_menu(session: AsyncSession = Depends(get_db)):
    repo = MenuRepository(session)
    return await repo.list_menu_items(available_only=False)


@router.get("/stations", response_model=List[StationRead])
async def list_stations(session: AsyncSession = Depends(get_db)):
    repo = MenuRepository(session)
    return await repo.list_stations(active_only=False)


@router.get("/{item_id}", response_model=MenuItemRead)
async def get_menu_item(item_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    repo = MenuRepository(session)
    item = await repo.get_menu_item_by_id(item_id)
    if not item:
        raise NotFoundError(f"Menu item {item_id} not found", code="MENU_ITEM_NOT_FOUND")
    return item


# Admin endpoints
@router.post(
    "",
    response_model=MenuItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_menu_item(data: MenuItemCreate, session: AsyncSession = Depends(get_db)):
    repo = MenuRepository(session)
    item = MenuItem(**data.model_dump())
    return await repo.create_menu_item(item)


@router.put(
    "/{item_id}",
    response_model=MenuItemRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_menu_item(
    item_id: uuid.UUID,
    data: MenuItemUpdate,
    session: AsyncSession = Depends(get_db),
):
    repo = MenuRepository(session)
    item = await repo.get_menu_item_by_id(item_id)
    if not item:
        raise NotFoundError("Menu item not found", code="MENU_ITEM_NOT_FOUND")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    return await repo.update_menu_item(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_menu_item(item_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    repo = MenuRepository(session)
    item = await repo.get_menu_item_by_id(item_id)
    if not item:
        raise NotFoundError("Menu item not found", code="MENU_ITEM_NOT_FOUND")
    await repo.delete_menu_item(item)
