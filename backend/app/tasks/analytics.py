import asyncio
from app.core.logging import logger
from app.db.session import async_session_factory
from app.services.analytics_service import AnalyticsService
from app.tasks.celery_app import celery_app


async def _precompute_analytics():
    async with async_session_factory() as session:
        service = AnalyticsService(session)
        summary = await service.get_summary()
        accuracy = await service.get_accuracy_metrics()
        logger.info(
            f"Precomputed admin analytics: orders={summary.total_orders_today}, MAE={accuracy.mae}"
        )


@celery_app.task(name="app.tasks.analytics.precompute_analytics_task")
def precompute_analytics_task():
    try:
        asyncio.run(_precompute_analytics())
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error precomputing analytics: {e}")
        return {"status": "error", "message": str(e)}
