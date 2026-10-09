from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "queuesense_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.forecast",
        "app.tasks.retrain",
        "app.tasks.analytics",
        "app.tasks.notifications",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-forecast-every-minute": {
            "task": "app.tasks.forecast.refresh_forecast_cache",
            "schedule": 60.0,
        },
        "nightly-retrain-model": {
            "task": "app.tasks.retrain.retrain_model_task",
            "schedule": crontab(hour=2, minute=0),
        },
        "precompute-analytics-hourly": {
            "task": "app.tasks.analytics.precompute_analytics_task",
            "schedule": crontab(minute=0),
        },
    },
)
