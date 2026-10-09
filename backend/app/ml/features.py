from typing import Any, Dict, List
import pandas as pd

FEATURE_COLUMNS: List[str] = [
    "items_ahead_tea",
    "items_ahead_tawa",
    "items_ahead_fryer",
    "minutes_ahead_tea",
    "minutes_ahead_tawa",
    "minutes_ahead_fryer",
    "items_in_this_order",
    "people_in_zone",
    "estimated_walk_ins",
    "hour",
    "day_of_week",
    "minutes_since_last_bell",
    "is_break",
    "cooks_tea",
    "cooks_tawa",
    "cooks_fryer",
]


def build_feature_dict(
    items_ahead_per_station: Dict[str, int],
    minutes_ahead_per_station: Dict[str, float],
    items_in_this_order: int,
    people_in_zone: int,
    estimated_walk_ins: int,
    hour: int,
    day_of_week: int,
    minutes_since_last_bell: int,
    is_break: bool,
    active_cooks_per_station: Dict[str, int],
) -> Dict[str, Any]:
    """
    Shared feature builder used for both training dataset generation and real-time prediction.
    """
    def _get_st(data_dict: dict, name: str, default: Any) -> Any:
        for k, v in data_dict.items():
            if name in k.lower():
                return v
        return default

    features: Dict[str, Any] = {
        "items_ahead_tea": _get_st(items_ahead_per_station, "tea", 0),
        "items_ahead_tawa": _get_st(items_ahead_per_station, "tawa", 0),
        "items_ahead_fryer": _get_st(items_ahead_per_station, "fryer", 0),
        "minutes_ahead_tea": float(_get_st(minutes_ahead_per_station, "tea", 0.0)),
        "minutes_ahead_tawa": float(_get_st(minutes_ahead_per_station, "tawa", 0.0)),
        "minutes_ahead_fryer": float(_get_st(minutes_ahead_per_station, "fryer", 0.0)),
        "items_in_this_order": items_in_this_order,
        "people_in_zone": people_in_zone,
        "estimated_walk_ins": estimated_walk_ins,
        "hour": hour,
        "day_of_week": day_of_week,
        "minutes_since_last_bell": minutes_since_last_bell,
        "is_break": 1 if is_break else 0,
        "cooks_tea": _get_st(active_cooks_per_station, "tea", 2),
        "cooks_tawa": _get_st(active_cooks_per_station, "tawa", 2),
        "cooks_fryer": _get_st(active_cooks_per_station, "fryer", 1),
    }
    return features


def feature_dict_to_dataframe(feature_dict: Dict[str, Any]) -> pd.DataFrame:
    """Converts feature dictionary to single-row DataFrame ordered by FEATURE_COLUMNS."""
    row = {col: feature_dict.get(col, 0) for col in FEATURE_COLUMNS}
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
