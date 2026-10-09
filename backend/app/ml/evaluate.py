from typing import Any, Dict
import numpy as np
import pandas as pd


def compute_pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    err = y_true - y_pred
    return float(np.mean(np.maximum(alpha * err, (alpha - 1.0) * err)))


def evaluate_predictions(
    y_true: np.ndarray,
    pred_low: np.ndarray,
    pred_median: np.ndarray,
    pred_high: np.ndarray,
) -> Dict[str, Any]:
    """
    Computes regression and coverage metrics:
    - MAE (on median)
    - RMSE (on median)
    - Coverage of 80% interval [pred_low, pred_high]
    - Pinball loss for q10, q50, q90
    """
    y_true_arr = np.array(y_true, dtype=float)
    p_low = np.array(pred_low, dtype=float)
    p_med = np.array(pred_median, dtype=float)
    p_high = np.array(pred_high, dtype=float)

    mae = float(np.mean(np.abs(y_true_arr - p_med)))
    rmse = float(np.sqrt(np.mean((y_true_arr - p_med) ** 2)))

    # Coverage: what fraction of actual values fell inside [p_low, p_high]
    in_interval = (y_true_arr >= p_low) & (y_true_arr <= p_high)
    coverage = float(np.mean(in_interval))

    q10_loss = compute_pinball_loss(y_true_arr, p_low, 0.10)
    q50_loss = compute_pinball_loss(y_true_arr, p_med, 0.50)
    q90_loss = compute_pinball_loss(y_true_arr, p_high, 0.90)

    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "coverage_80": round(coverage, 4),
        "q10_pinball_loss": round(q10_loss, 3),
        "q50_pinball_loss": round(q50_loss, 3),
        "q90_pinball_loss": round(q90_loss, 3),
        "sample_count": len(y_true_arr),
    }


def compute_baseline_mae(df: pd.DataFrame) -> float:
    """Computes MAE of baseline formula against actual_wait."""
    waits = []
    for _, row in df.iterrows():
        # Baseline approx: max of (minutes_ahead + own_items)
        tea_wait = row.get("minutes_ahead_tea", 0) / max(1, row.get("cooks_tea", 2))
        tawa_wait = row.get("minutes_ahead_tawa", 0) / max(1, row.get("cooks_tawa", 2))
        fryer_wait = row.get("minutes_ahead_fryer", 0) / max(1, row.get("cooks_fryer", 1))
        est = max(tea_wait, tawa_wait, fryer_wait) + (row.get("items_in_this_order", 1) * 2.0)
        waits.append(max(1.0, est))

    baseline_preds = np.array(waits)
    actuals = df["actual_wait"].to_numpy()
    return float(np.mean(np.abs(actuals - baseline_preds)))
