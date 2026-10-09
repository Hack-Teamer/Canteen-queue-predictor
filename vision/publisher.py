from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("vision.publisher")


class CountPublisher:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        zone_id: str = "canteen_queue_zone",
        timeout: float = 4.0,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.zone_id = zone_id
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def publish_count(self, people_count: int, captured_at: Optional[datetime] = None) -> bool:
        if captured_at is None:
            captured_at = datetime.now(timezone.utc)

        payload = {
            "people_count": people_count,
            "zone_id": self.zone_id,
            "captured_at": captured_at.isoformat(),
        }
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

        endpoint = f"{self.api_url}/api/v1/vision/count"
        try:
            resp = self.client.post(endpoint, json=payload, headers=headers)
            if resp.status_code == 200:
                logger.info(f"Published count={people_count} to {endpoint} successfully.")
                return True
            else:
                logger.warning(f"Failed to publish count: HTTP {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error publishing count to backend: {e}")
            return False

    def close(self) -> None:
        self.client.close()
