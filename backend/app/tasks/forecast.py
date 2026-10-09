import asyncio
from app.core.logging import logger
from app.core.redis import get_redis_client
from app.db.session import async_session_factory
from app.services.forecast_service import ForecastService
from app.tasks.celery_app import celery_app


async def _refresh_forecast():
    redis = await get_redis_client()
    async with async_session_factory() as session:
        service = ForecastService(session, redis)
        forecast = await service.get_next_30_minutes_forecast(force_refresh=True)
        logger.info(f"Forecast cache refreshed. Best slot: {forecast.best_slot.slot_time}")


@celery_app.task(name="app.tasks.forecast.refresh_forecast_cache")
def refresh_forecast_cache():
    try:
        asyncio.run(_refresh_forecast())
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error in refresh_forecast_cache task: {e}")
        return {"status": "error", "message": str(e)}
