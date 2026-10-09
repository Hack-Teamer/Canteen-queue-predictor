import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.order import Order


class QueueEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "queue_events"

    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="events")

    __table_args__ = (
        Index("ix_queue_events_order_id", "order_id"),
    )
