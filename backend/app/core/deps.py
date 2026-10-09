from typing import AsyncGenerator, Callable, List
import uuid
import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, RateLimitError, UnauthorizedError
from app.core.redis import RedisKeys, get_redis_client
from app.core.security import decode_token
from app.db.session import async_session_factory
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> aioredis.Redis:
    return await get_redis_client()


async def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not auth or not auth.credentials:
        raise UnauthorizedError("Not authenticated", code="AUTH_REQUIRED")

    payload = decode_token(auth.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type", code="INVALID_TOKEN_TYPE")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Invalid token subject", code="INVALID_TOKEN")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError("Invalid user ID format", code="INVALID_USER_ID")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User does not exist or is inactive", code="USER_INACTIVE")

    return user


def require_role(*roles: UserRole) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError(
                f"Role '{current_user.role.value}' does not have access. Required: {[r.value for r in roles]}",
                code="FORBIDDEN_ROLE",
            )
        return current_user

    return role_checker


async def verify_vision_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if x_api_key != settings.VISION_API_KEY:
        raise UnauthorizedError("Invalid Vision API Key", code="INVALID_API_KEY")
    return x_api_key


async def rate_limiter(
    prefix: str,
    limit: int,
    identifier: str,
    redis: aioredis.Redis,
) -> None:
    key = RedisKeys.rate_limit_key(prefix, identifier)
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    if current > limit:
        raise RateLimitError(
            f"Rate limit exceeded. Maximum {limit} requests per minute.",
            code="RATE_LIMIT_EXCEEDED",
        )
