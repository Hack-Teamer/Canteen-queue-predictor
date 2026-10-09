import datetime
from typing import Any, Dict, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd

from app.ml.evaluate import compute_baseline_mae, evaluate_predictions
from app.ml.features import FEATURE_COLUMNS


def train_quantile_models(
    df: pd.DataFrame,
    test_ratio: float = 0.20,
    n_estimators: int = 150,
    learning_rate: float = 0.05,
) -> Dict[str, Any]:
    """
    Trains LightGBM quantile regression models for alpha = 0.10, 0.50, 0.90.
    Uses time-based holdout split (last test_ratio portion) to avoid lookahead bias.
    """
    # Verify features exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    X = df[FEATURE_COLUMNS]
    y = df["actual_wait"]

    # Time-based holdout split (NOT random shuffle)
    split_idx = int(len(df) * (1.0 - test_ratio))
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

    lgb_params = {
        "n_estimators": n_estimators,
        "learning_rate": learning_rate,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 20,
        "random_state": 42,
        "verbose": -1,
    }

    # Train q10
    model_q10 = lgb.LGBMRegressor(objective="quantile", alpha=0.10, **lgb_params)
    model_q10.fit(X_train, y_train)

    # Train q50 (median)
    model_q50 = lgb.LGBMRegressor(objective="quantile", alpha=0.50, **lgb_params)
    model_q50.fit(X_train, y_train)

    # Train q90
    model_q90 = lgb.LGBMRegressor(objective="quantile", alpha=0.90, **lgb_params)
    model_q90.fit(X_train, y_train)

    # Evaluate on holdout
    pred_low = model_q10.predict(X_val)
    pred_med = model_q50.predict(X_val)
    pred_high = model_q90.predict(X_val)

    # Post-process validation predictions: ensure monotonic ordering
    pred_low = np.maximum(1.0, pred_low)
    pred_med = np.maximum(pred_low, pred_med)
    pred_high = np.maximum(pred_med, pred_high)

    metrics = evaluate_predictions(y_val.to_numpy(), pred_low, pred_med, pred_high)
    baseline_mae = compute_baseline_mae(df.iloc[split_idx:])
    metrics["baseline_mae"] = round(baseline_mae, 3)
    if baseline_mae > 0:
        improvement = ((baseline_mae - metrics["mae"]) / baseline_mae) * 100.0
        metrics["improvement_vs_baseline_percent"] = round(improvement, 2)
    else:
        metrics["improvement_vs_baseline_percent"] = 0.0

    # Feature importances from median model
    importances = dict(zip(FEATURE_COLUMNS, model_q50.feature_importances_))

    version = f"v_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return {
        "version": version,
        "model_q10": model_q10,
        "model_q50": model_q50,
        "model_q90": model_q90,
        "metrics": metrics,
        "feature_importances": {k: float(v) for k, v in importances.items()},
    }
