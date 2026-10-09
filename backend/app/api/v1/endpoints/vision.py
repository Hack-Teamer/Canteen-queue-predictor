from datetime import datetime, timezone
import json
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_redis, verify_vision_api_key
from app.core.redis import RedisChannels, RedisKeys
from app.core.websocket_manager import ws_manager
from app.models.crowd_snapshot import CrowdSnapshot
from app.repositories.crowd_repo import CrowdRepository
from app.schemas.vision import VisionCountInput, VisionCountResponse

router = APIRouter()


@router.post("/count", response_model=VisionCountResponse)
async def ingest_vision_count(
    payload: VisionCountInput,
    api_key: str = Depends(verify_vision_api_key),
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    crowd_repo = CrowdRepository(session)

    # 1. Store raw snapshot
    snapshot = CrowdSnapshot(
        people_count=payload.people_count,
        zone_id=payload.zone_id,
        captured_at=payload.captured_at,
    )
    await crowd_repo.add_snapshot(snapshot)

    # 2. 5-sample moving average
    recent = await crowd_repo.get_recent_snapshots(limit=4, zone_id=payload.zone_id)
    counts = [s.people_count for s in recent]
    counts.append(payload.people_count)
    smoothed = round(sum(counts) / float(len(counts)), 1)

    # 3. Write to Redis with TTL
    if redis:
        await redis.set(RedisKeys.CROWD_LATEST, str(smoothed), ex=settings.CROWD_STALE_SECONDS)
        await redis.lpush(RedisKeys.CROWD_HISTORY, str(smoothed))
        await redis.ltrim(RedisKeys.CROWD_HISTORY, 0, 9)

    # 4. Broadcast real-time update
    update_data = {
        "type": "crowd_update",
        "zone_id": payload.zone_id,
        "count": smoothed,
        "captured_at": payload.captured_at.isoformat(),
    }
    await ws_manager.broadcast_queue(update_data)
    await ws_manager.broadcast_kitchen(update_data)

    return VisionCountResponse(
        status="success",
        raw_count=payload.people_count,
        smoothed_count=smoothed,
        captured_at=payload.captured_at,
        zone_id=payload.zone_id,
    )
