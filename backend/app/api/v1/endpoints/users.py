from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put("/me", response_model=UserRead)
async def update_user_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if update_data.name is not None:
        current_user.name = update_data.name
    if update_data.email is not None:
        current_user.email = update_data.email
    await session.flush()
    return current_user
