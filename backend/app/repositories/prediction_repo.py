from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_prediction(self, prediction: Prediction) -> Prediction:
        self.session.add(prediction)
        await self.session.flush()
        return prediction

    async def get_latest_by_order(self, order_id: uuid.UUID) -> Optional[Prediction]:
        stmt = (
            select(Prediction)
            .where(Prediction.order_id == order_id)
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_actual_wait(
        self, order_id: uuid.UUID, actual_wait_minutes: float
    ) -> Optional[Prediction]:
        prediction = await self.get_latest_by_order(order_id)
        if prediction:
            prediction.actual_wait_minutes = actual_wait_minutes
            await self.session.flush()
        return prediction

    async def get_training_dataset(self, min_rows: int = 500) -> List[Prediction]:
        stmt = (
            select(Prediction)
            .where(Prediction.actual_wait_minutes.isnot(None))
            .order_by(Prediction.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_completed_predictions(self) -> int:
        stmt = select(func.count(Prediction.id)).where(Prediction.actual_wait_minutes.isnot(None))
        result = await self.session.execute(stmt)
        return result.scalar() or 0
