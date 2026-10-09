from app.ml.features import FEATURE_COLUMNS, build_feature_dict, feature_dict_to_dataframe


def test_build_feature_dict_keys():
    features = build_feature_dict(
        items_ahead_per_station={"tea": 3, "tawa": 5, "fryer": 2},
        minutes_ahead_per_station={"tea": 4.5, "tawa": 12.0, "fryer": 6.0},
        items_in_this_order=2,
        people_in_zone=10,
        estimated_walk_ins=4,
        hour=12,
        day_of_week=2,
        minutes_since_last_bell=15,
        is_break=True,
        active_cooks_per_station={"tea": 2, "tawa": 2, "fryer": 1},
    )

    for col in FEATURE_COLUMNS:
        assert col in features

    assert features["items_ahead_tea"] == 3
    assert features["minutes_ahead_tawa"] == 12.0
    assert features["items_in_this_order"] == 2
    assert features["estimated_walk_ins"] == 4
    assert features["is_break"] == 1
    assert features["cooks_tea"] == 2


def test_feature_dict_to_dataframe():
    features = build_feature_dict(
        items_ahead_per_station={},
        minutes_ahead_per_station={},
        items_in_this_order=1,
        people_in_zone=0,
        estimated_walk_ins=0,
        hour=9,
        day_of_week=0,
        minutes_since_last_bell=60,
        is_break=False,
        active_cooks_per_station={},
    )
    df = feature_dict_to_dataframe(features)
    assert len(df) == 1
    assert list(df.columns) == FEATURE_COLUMNS
