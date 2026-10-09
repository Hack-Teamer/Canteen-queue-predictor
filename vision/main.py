import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
import yaml

from detector import PersonDetector
from publisher import CountPublisher
from smoothing import MovingAverageSmoother
from zone import QueueZone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vision.main")

running = True


def signal_handler(sig, frame):
    global running
    logger.info("Termination signal received. Stopping vision pipeline...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_config(config_path: str = "config.yaml") -> dict:
    p = Path(config_path)
    if not p.exists():
        # Fallback defaults
        return {
            "video_source": "0",
            "zone_id": "canteen_queue_zone",
            "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
            "backend": {"api_url": "http://localhost:8000", "api_key": "vision-secret-api-key-2024"},
            "intervals": {"detection_interval_sec": 1.0, "publish_interval_sec": 3.0, "smoothing_window": 5},
        }
    with open(p, "r") as f:
        return yaml.safe_load(f)


def main():
    global running
    config = load_config()

    zone = QueueZone(polygon_coords=config["polygon"], zone_id=config.get("zone_id", "canteen_queue_zone"))
    detector = PersonDetector()
    smoother = MovingAverageSmoother(window_size=config["intervals"].get("smoothing_window", 5))
    publisher = CountPublisher(
        api_url=config["backend"]["api_url"],
        api_key=config["backend"]["api_key"],
        zone_id=zone.zone_id,
    )

    source = config.get("video_source", "0")
    # Try converting numeric string to int camera index
    try:
        source_idx = int(source)
    except ValueError:
        source_idx = source

    cap = cv2.VideoCapture(source_idx)
    is_live_stream = cap.isOpened()

    if not is_live_stream:
        logger.warning(f"Unable to open video source '{source}'. Running in mock camera mode for pipeline operation.")

    last_publish_time = 0.0
    detection_interval = config["intervals"].get("detection_interval_sec", 1.0)
    publish_interval = config["intervals"].get("publish_interval_sec", 3.0)

    logger.info(f"Vision service started for zone '{zone.zone_id}'. Publishing to {config['backend']['api_url']}")

    try:
        while running:
            now = time.time()

            if is_live_stream:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame read failed or video ended. Rewinding / retrying...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(1.0)
                    continue
            else:
                # Generate synthetic test frame (640x480 black background)
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

            # Detect feet positions
            feet_points = detector.detect_person_feet_positions(frame)

            # Count people inside polygon zone
            count_in_zone = 0
            for pt in feet_points:
                if zone.is_inside(pt):
                    count_in_zone += 1

            smoothed_count = smoother.add_sample(count_in_zone)

            # Publish periodically
            if now - last_publish_time >= publish_interval:
                publisher.publish_count(
                    people_count=int(round(smoothed_count)),
                    captured_at=datetime.now(timezone.utc),
                )
                last_publish_time = now

            time.sleep(detection_interval)

    finally:
        if is_live_stream:
            cap.release()
        publisher.close()
        logger.info("Vision service stopped cleanly.")


if __name__ == "__main__":
    main()
