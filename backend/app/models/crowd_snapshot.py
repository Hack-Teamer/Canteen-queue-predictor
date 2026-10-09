from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class CrowdSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "crowd_snapshots"

    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_id: Mapped[str] = mapped_column(String(100), default="canteen_queue_zone", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_crowd_snapshots_captured_at", "captured_at"),
    )
