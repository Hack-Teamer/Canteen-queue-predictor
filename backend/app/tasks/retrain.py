import asyncio
import pandas as pd
from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session_factory
from app.ml.features import FEATURE_COLUMNS
from app.ml.registry import model_registry
from app.ml.simulator import generate_canteen_dataset
from app.ml.trainer import train_quantile_models
from app.repositories.prediction_repo import PredictionRepository
from app.tasks.celery_app import celery_app


async def _run_nightly_retraining():
    logger.info("Starting nightly ML model retraining pipeline...")
    async with async_session_factory() as session:
        pred_repo = PredictionRepository(session)
        preds = await pred_repo.get_training_dataset(min_rows=1)

    db_rows = []
    for p in preds:
        if p.actual_wait_minutes is not None and isinstance(p.features, dict):
            row = {**p.features, "actual_wait": p.actual_wait_minutes}
            db_rows.append(row)

    min_rows = settings.MIN_RETRAIN_ROWS
    needed_from_sim = max(0, min_rows - len(db_rows))

    if needed_from_sim > 0:
        logger.info(f"DB has {len(db_rows)} samples. Generating {needed_from_sim} synthetic samples with SimPy...")
        sim_df = generate_canteen_dataset(target_orders=needed_from_sim, seed=123)
        if db_rows:
            db_df = pd.DataFrame(db_rows)
            combined_df = pd.concat([sim_df, db_df], ignore_index=True)
        else:
            combined_df = sim_df
    else:
        combined_df = pd.DataFrame(db_rows)

    # Train LightGBM quantile regression
    train_result = train_quantile_models(combined_df)
    new_version = train_result["version"]
    new_metrics = train_result["metrics"]
    logger.info(f"Retraining complete for version {new_version}. Holdout MAE: {new_metrics['mae']}")

    # Check against current active model
    active_bundle = model_registry.get_active_model()
    should_promote = True
    if active_bundle and "metrics" in active_bundle:
        curr_mae = active_bundle["metrics"].get("mae", 999.0)
        new_mae = new_metrics.get("mae", 999.0)
        should_promote = new_mae < curr_mae
        logger.info(f"Comparing holdout MAE: new={new_mae:.3f} vs active={curr_mae:.3f} -> promote={should_promote}")

    model_registry.save_model(
        version=new_version,
        models_dict=train_result,
        metrics=new_metrics,
        feature_importances=train_result["feature_importances"],
    )

    if should_promote:
        model_registry.promote(new_version)
        logger.info(f"Model {new_version} promoted to production!")
    else:
        logger.info(f"Model {new_version} kept in registry without promotion.")


@celery_app.task(name="app.tasks.retrain.retrain_model_task")
def retrain_model_task():
    try:
        asyncio.run(_run_nightly_retraining())
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error during nightly retraining: {e}")
        return {"status": "error", "message": str(e)}
