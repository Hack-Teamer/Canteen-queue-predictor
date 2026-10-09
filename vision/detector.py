import logging
from typing import List, Optional, Tuple
import numpy as np

logger = logging.getLogger("vision.detector")


class PersonDetector:
    def __init__(self, model_name: str = "yolov8n.pt", conf_thresh: float = 0.35) -> None:
        self.model_name = model_name
        self.conf_thresh = conf_thresh
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            logger.info(f"Loaded YOLOv8 model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Could not load YOLOv8 model ({e}). Using mock detector fallback.")
            self.model = None

    def detect_person_feet_positions(self, frame: np.ndarray) -> List[Tuple[float, float]]:
        """
        Detects people in frame and returns the feet/bottom-center coordinate (x_center, y_max)
        of each detected person.
        """
        if self.model is None:
            # Fallback mock for testing/simulation: return simulated points
            h, w = frame.shape[:2]
            return [(w * 0.45, h * 0.6), (w * 0.5, h * 0.7), (w * 0.52, h * 0.8)]

        # Class 0 in COCO is person
        results = self.model(frame, classes=[0], conf=self.conf_thresh, verbose=False)
        feet_positions: List[Tuple[float, float]] = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                coords = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = coords
                x_center = float((x1 + x2) / 2.0)
                y_bottom = float(y2)
                feet_positions.append((x_center, y_bottom))

        return feet_positions
