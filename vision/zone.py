from typing import List, Tuple
import cv2
import numpy as np


class QueueZone:
    def __init__(self, polygon_coords: List[List[int]], zone_id: str = "canteen_queue_zone") -> None:
        self.zone_id = zone_id
        self.polygon = np.array(polygon_coords, dtype=np.int32)

    def is_inside(self, point: Tuple[float, float]) -> bool:
        """
        Point-in-polygon test.
        Returns True if the point is inside or on the boundary of the polygon.
        """
        pt = (float(point[0]), float(point[1]))
        res = cv2.pointPolygonTest(self.polygon, pt, measureDist=False)
        return res >= 0
