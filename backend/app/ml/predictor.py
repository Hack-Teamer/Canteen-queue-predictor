import math
from typing import Any, Dict, Optional
import numpy as np

from app.core.logging import logger
from app.ml.features import feature_dict_to_dataframe
from app.ml.registry import model_registry
from app.schemas.order import WaitRange


class WaitTimePredictor:
    def __init__(self) -> None:
        self._cached_bundle: Optional[Dict[str, Any]] = None
        self._cached_version: Optional[str] = None

    def _get_bundle(self) -> Optional[Dict[str, Any]]:
        active_ver = model_registry.get_active_version()
        if not active_ver:
            return None
        if self._cached_bundle is not None and self._cached_version == active_ver:
            return self._cached_bundle

        bundle = model_registry.get_active_model()
        if bundle:
            self._cached_bundle = bundle
            self._cached_version = active_ver
        return bundle

    def predict(self, feature_dict: Dict[str, Any]) -> Optional[WaitRange]:
        """
        Uses active quantile regression model to predict low (q10), median (q50), and high (q90) wait times.
        Enforces low <= median <= high, whole minutes (floor low, ceil high, min 1).
        Returns None if model is unavailable or encounters error, triggering baseline fallback.
        """
        try:
            bundle = self._get_bundle()
            if bundle is None:
                return None

            model_q10 = bundle["q10"]
            model_q50 = bundle["q50"]
            model_q90 = bundle["q90"]
            version = bundle.get("version", "ml_v1")

            df_features = feature_dict_to_dataframe(feature_dict)

            raw_q10 = float(model_q10.predict(df_features)[0])
            raw_q50 = float(model_q50.predict(df_features)[0])
            raw_q90 = float(model_q90.predict(df_features)[0])

            # Monotonic adjustment
            raw_q10 = max(1.0, raw_q10)
            raw_q50 = max(raw_q10, raw_q50)
            raw_q90 = max(raw_q50, raw_q90)

            # Rounding: floor low, ceil high, round median, min 1
            low = max(1, math.floor(raw_q10))
            median = max(1, round(raw_q50))
            high = max(median, math.ceil(raw_q90))

            if low > median:
                low = median
            if high < median:
                high = median

            return WaitRange(
                low=int(low),
                median=int(median),
                high=int(high),
                source="ml",
                model_version=version,
            )
        except Exception as e:
            logger.warning(f"Predictor error: {e}. Falling back to baseline.")
            return None


predictor = WaitTimePredictor()
