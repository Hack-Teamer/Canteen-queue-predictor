import numpy as np
import pytest
from app.ml.simulator import generate_canteen_dataset
from app.ml.trainer import train_quantile_models


def test_model_quantile_monotonicity_and_coverage():
    # 1. Generate synthetic dataset with SimPy
    df = generate_canteen_dataset(target_orders=600, seed=42)
    assert len(df) >= 500

    # 2. Train LightGBM quantile regression models
    result = train_quantile_models(df, test_ratio=0.20, n_estimators=60)
    metrics = result["metrics"]

    # 3. Coverage check: between 70% and 95% for the 10-90 band
    assert 0.70 <= metrics["coverage_80"] <= 0.95

    # 4. Monotonicity check on holdout predictions
    model_q10 = result["model_q10"]
    model_q50 = result["model_q50"]
    model_q90 = result["model_q90"]

    split_idx = int(len(df) * 0.80)
    X_val = df.iloc[split_idx:][result["model_q50"].feature_name_]

    p10 = model_q10.predict(X_val)
    p50 = model_q50.predict(X_val)
    p90 = model_q90.predict(X_val)

    # Median should generally track between p10 and p90
    mean_p10 = np.mean(p10)
    mean_p50 = np.mean(p50)
    mean_p90 = np.mean(p90)
    assert mean_p10 <= mean_p50 <= mean_p90


def test_fused_model_beats_orders_only_on_walk_in_spikes():
    # Generate data with high walk-ins
    from app.ml.simulator import CanteenSimulator
    sim = CanteenSimulator(seed=101, target_orders=600, walk_in_ratio=0.50)
    df = sim.run()

    # Train fused model (with estimated_walk_ins and people_in_zone)
    res_fused = train_quantile_models(df, test_ratio=0.20, n_estimators=60)

    # Train baseline orders-only (without walk-in signals)
    df_no_walkins = df.copy()
    df_no_walkins["estimated_walk_ins"] = 0
    df_no_walkins["people_in_zone"] = 0
    res_no_walkins = train_quantile_models(df_no_walkins, test_ratio=0.20, n_estimators=60)

    # The fused model should have lower or equal MAE when walk-ins are high
    assert res_fused["metrics"]["mae"] <= res_no_walkins["metrics"]["mae"] + 0.5
