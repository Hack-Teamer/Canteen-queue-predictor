import argparse
from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from app.core.logging import logger
from app.ml.registry import model_registry
from app.ml.simulator import generate_canteen_dataset
from app.ml.trainer import train_quantile_models


def main():
    parser = argparse.ArgumentParser(description="Train LightGBM Quantile regression models")
    parser.add_argument("--data", type=str, default="", help="Path to input CSV data (optional)")
    parser.add_argument("--orders", type=int, default=5000, help="Orders to simulate if no data file")
    parser.add_argument("--promote", action="store_true", default=True, help="Promote trained model to active")
    args = parser.parse_args()

    if args.data and Path(args.data).exists():
        logger.info(f"Loading training data from {args.data}...")
        df = pd.read_csv(args.data)
    else:
        logger.info(f"No data file provided. Generating {args.orders} samples using SimPy simulator...")
        df = generate_canteen_dataset(target_orders=args.orders, seed=42)

    logger.info(f"Training LightGBM quantile regression models on {len(df)} samples...")
    train_result = train_quantile_models(df)
    version = train_result["version"]
    metrics = train_result["metrics"]

    logger.info(f"Trained model {version}:")
    logger.info(f"  Holdout MAE: {metrics['mae']} mins")
    logger.info(f"  Holdout RMSE: {metrics['rmse']} mins")
    logger.info(f"  Coverage [q10, q90]: {metrics['coverage_80'] * 100:.1f}%")
    logger.info(f"  Baseline MAE: {metrics['baseline_mae']} mins")
    logger.info(f"  Improvement: {metrics['improvement_vs_baseline_percent']}%")

    model_registry.save_model(
        version=version,
        models_dict=train_result,
        metrics=metrics,
        feature_importances=train_result["feature_importances"],
    )

    if args.promote:
        model_registry.promote(version)
        logger.info(f"Model {version} is now active in production!")


if __name__ == "__main__":
    main()
