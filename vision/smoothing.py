from collections import deque
from typing import Deque


class MovingAverageSmoother:
    def __init__(self, window_size: int = 5) -> None:
        self.window_size = window_size
        self.buffer: Deque[float] = deque(maxlen=window_size)

    def add_sample(self, val: float) -> float:
        self.buffer.append(float(val))
        return self.get_smoothed()

    def get_smoothed(self) -> float:
        if not self.buffer:
            return 0.0
        return sum(self.buffer) / len(self.buffer)

    def get_integer_estimate(self) -> int:
        return int(round(self.get_smoothed()))
