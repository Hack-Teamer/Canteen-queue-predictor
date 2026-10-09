import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.deps import get_db, get_redis
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.seed import seed_data
from app.main import app
from app.models.user import User, UserRole

# Use in-memory SQLite for high-speed tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        await seed_data(session)
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    if hasattr(redis, "aclose"):
        await redis.aclose()
    else:
        await redis.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def student_auth_headers(db_session: AsyncSession) -> dict:
    # student@queuesense.edu seeded in seed_data
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "student@queuesense.edu",
        "role": UserRole.STUDENT.value,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def kitchen_auth_headers(db_session: AsyncSession) -> dict:
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000002",
        "email": "kitchen@queuesense.edu",
        "role": UserRole.KITCHEN.value,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(db_session: AsyncSession) -> dict:
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000003",
        "email": "admin@queuesense.edu",
        "role": UserRole.ADMIN.value,
    })
    return {"Authorization": f"Bearer {token}"}
