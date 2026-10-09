import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_redis
from app.schemas.queue import QueueSummaryResponse
from app.services.queue_service import QueueService

router = APIRouter()


@router.get("", response_model=QueueSummaryResponse)
async def get_queue_summary(
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = QueueService(session, redis)
    return await service.get_queue_summary()
