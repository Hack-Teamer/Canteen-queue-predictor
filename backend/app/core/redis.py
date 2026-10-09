from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

redis_client: Optional[aioredis.Redis] = None


class RedisKeys:
    QUEUE_ACTIVE = "queue:active"
    CROWD_LATEST = "crowd:latest"
    CROWD_HISTORY = "crowd:history"
    FORECAST_NEXT30 = "forecast:next30"

    @staticmethod
    def queue_station(station_id: str) -> str:
        return f"queue:station:{station_id}"

    @staticmethod
    def load_station(station_id: str) -> str:
        return f"load:station:{station_id}"

    @staticmethod
    def token_counter(date_str: str) -> str:
        return f"token:counter:{date_str}"

    @staticmethod
    def idempotency_key(key: str) -> str:
        return f"idempotency:{key}"

    @staticmethod
    def rate_limit_key(prefix: str, identifier: str) -> str:
        return f"ratelimit:{prefix}:{identifier}"


class RedisChannels:
    QUEUE_UPDATES = "queue_updates"
    KITCHEN_UPDATES = "kitchen_updates"

    @staticmethod
    def order_channel(order_id: str) -> str:
        return f"order:{order_id}"


async def get_redis_client() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def close_redis_client() -> None:
    global redis_client
    if redis_client is not None:
        try:
            if hasattr(redis_client, "aclose"):
                await redis_client.aclose()
            else:
                await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis: {e}")
        finally:
            redis_client = None
