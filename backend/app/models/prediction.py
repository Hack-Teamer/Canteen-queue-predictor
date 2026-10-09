import enum
import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import Enum, Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.order import Order


class PredictionSource(str, enum.Enum):
    ML = "ml"
    BASELINE = "baseline"


class Prediction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "predictions"

    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[PredictionSource] = mapped_column(
        Enum(PredictionSource, values_callable=lambda obj: [e.value for e in obj]),
        default=PredictionSource.BASELINE,
        nullable=False,
    )
    pred_low: Mapped[int] = mapped_column(Float, nullable=False)
    pred_median: Mapped[int] = mapped_column(Float, nullable=False)
    pred_high: Mapped[int] = mapped_column(Float, nullable=False)
    actual_wait_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    features: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_created_at", "created_at"),
    )
