from fastapi import APIRouter, Depends, Request
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_redis, rate_limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
async def register_student(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    service = AuthService(session)
    user = await service.register_student(data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    # Rate limit by IP or email
    client_ip = request.client.host if request.client else data.email
    await rate_limiter(
        prefix="login",
        limit=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
        identifier=client_ip,
        redis=redis,
    )
    service = AuthService(session)
    return await service.authenticate(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_db),
):
    service = AuthService(session)
    return await service.refresh_tokens(data.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
