from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.core.exceptions import NotFoundError
from app.ml.registry import model_registry
from app.ml.simulator import generate_canteen_dataset
from app.ml.trainer import train_quantile_models
from app.models.user import UserRole
from app.repositories.crowd_repo import CrowdRepository
from app.repositories.menu_repo import MenuRepository
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.admin import (
    AccuracyMetrics,
    AdminSummary,
    ModelInfo,
    PeakHourStat,
    PopularItemStat,
    RetrainRequest,
    RetrainResponse,
    RollbackResponse,
    StationStat,
)
from app.schemas.menu import StationRead, StationUpdate
from app.services.analytics_service import AnalyticsService

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("/summary", response_model=AdminSummary)
async def get_admin_summary(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return await service.get_summary()


@router.get("/peak-hours", response_model=List[PeakHourStat])
async def get_peak_hours(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return await service.get_peak_hours()


@router.get("/stations", response_model=List[StationStat])
async def get_station_stats(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return await service.get_station_stats()


@router.put("/stations/{station_id}", response_model=StationRead)
async def update_station_cooks(
    station_id: uuid.UUID,
    data: StationUpdate,
    session: AsyncSession = Depends(get_db),
):
    repo = MenuRepository(session)
    if data.active_cooks is not None:
        updated = await repo.update_station_cooks(station_id, data.active_cooks)
        if not updated:
            raise NotFoundError("Station not found", code="STATION_NOT_FOUND")
        return updated
    station = await repo.get_station_by_id(station_id)
    if not station:
        raise NotFoundError("Station not found", code="STATION_NOT_FOUND")
    return station


@router.get("/popular-items", response_model=List[PopularItemStat])
async def get_popular_items(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return await service.get_popular_items()


@router.get("/accuracy", response_model=AccuracyMetrics)
async def get_accuracy_metrics(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return await service.get_accuracy_metrics()


@router.get("/crowd")
async def get_crowd_snapshots(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    repo = CrowdRepository(session)
    snapshots = await repo.get_recent_snapshots(limit=limit)
    return [
        {
            "id": str(s.id),
            "people_count": s.people_count,
            "zone_id": s.zone_id,
            "captured_at": s.captured_at.isoformat(),
        }
        for s in snapshots
    ]


@router.get("/model", response_model=ModelInfo)
async def get_model_info(session: AsyncSession = Depends(get_db)):
    service = AnalyticsService(session)
    return service.get_model_info()


@router.post("/model/retrain", response_model=RetrainResponse)
async def trigger_retrain(
    req: RetrainRequest,
    session: AsyncSession = Depends(get_db),
):
    # Retrieve DB actual waits
    pred_repo = PredictionRepository(session)
    completed_preds = await pred_repo.get_training_dataset(min_rows=1)

    # If rows < min_rows, top up with simulator data
    min_rows = req.min_rows or 500
    rows_needed = max(100, min_rows - len(completed_preds))
    sim_df = generate_canteen_dataset(target_orders=rows_needed, seed=42)

    # Train quantile LightGBM models
    train_result = train_quantile_models(sim_df)
    new_version = train_result["version"]
    new_metrics = train_result["metrics"]

    # Check against active model
    active_bundle = model_registry.get_active_model()
    should_promote = True
    if active_bundle and "metrics" in active_bundle and not req.force:
        curr_mae = active_bundle["metrics"].get("mae", 999.0)
        new_mae = new_metrics.get("mae", 999.0)
        should_promote = new_mae < curr_mae

    model_registry.save_model(
        version=new_version,
        models_dict=train_result,
        metrics=new_metrics,
        feature_importances=train_result["feature_importances"],
    )

    if should_promote:
        model_registry.promote(new_version)

    return RetrainResponse(
        status="success",
        message="Model retraining finished successfully.",
        new_version=new_version,
        promoted=should_promote,
        evaluation=new_metrics,
    )


@router.post("/model/rollback", response_model=RollbackResponse)
async def rollback_model(target_version: Optional[str] = None):
    res = model_registry.rollback(target_version)
    if not res:
        raise NotFoundError("Could not rollback: no valid previous model found", code="ROLLBACK_FAILED")
    return RollbackResponse(
        status="success",
        message=f"Model rolled back to active version {res}",
        active_version=res,
    )
