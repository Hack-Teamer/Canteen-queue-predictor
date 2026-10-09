from datetime import datetime
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_redis
from app.schemas.forecast import ForecastResponse, LeaveTimeResponse
from app.services.forecast_service import ForecastService

router = APIRouter()


@router.get("", response_model=ForecastResponse)
async def get_30_minute_forecast(
    force_refresh: bool = False,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = ForecastService(session, redis)
    return await service.get_next_30_minutes_forecast(force_refresh=force_refresh)


@router.get("/leave-time", response_model=LeaveTimeResponse)
async def get_leave_time_recommendation(
    next_class_at: datetime = Query(..., description="ISO 8601 timestamp of upcoming class start"),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = ForecastService(session, redis)
    return await service.calculate_leave_time(next_class_at)
