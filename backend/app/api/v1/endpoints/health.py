from datetime import datetime, timezone
from typing import Any, Dict
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_redis
from app.ml.registry import model_registry
from app.repositories.crowd_repo import CrowdRepository

router = APIRouter()


@router.get("")
async def liveness():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}


@router.get("/ready")
async def readiness(
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    health_status: Dict[str, Any] = {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }
    all_healthy = True

    # 1. Database check
    try:
        await session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False

    # 2. Redis check
    try:
        if redis:
            await redis.ping()
            health_status["checks"]["redis"] = {"status": "healthy"}
        else:
            health_status["checks"]["redis"] = {"status": "skipped"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False

    # 3. Model check
    active_model = model_registry.get_active_version()
    if active_model:
        health_status["checks"]["ml_model"] = {
            "status": "loaded",
            "active_version": active_model,
        }
    else:
        health_status["checks"]["ml_model"] = {
            "status": "baseline_fallback",
            "active_version": None,
        }

    # 4. Vision age check
    crowd_repo = CrowdRepository(session)
    latest_snapshot = await crowd_repo.get_latest_snapshot()
    if latest_snapshot:
        now = datetime.now(timezone.utc)
        snap_time = latest_snapshot.captured_at
        if snap_time.tzinfo is None:
            snap_time = snap_time.replace(tzinfo=timezone.utc)
        age_seconds = (now - snap_time).total_seconds()
        is_fresh = age_seconds <= settings.CROWD_STALE_SECONDS
        health_status["checks"]["vision"] = {
            "status": "fresh" if is_fresh else "stale",
            "age_seconds": round(age_seconds, 1),
            "latest_count": latest_snapshot.people_count,
        }
    else:
        health_status["checks"]["vision"] = {
            "status": "unavailable",
            "age_seconds": None,
        }

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=health_status)
