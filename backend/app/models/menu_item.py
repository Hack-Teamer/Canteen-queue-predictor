import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.station import Station
    from app.models.order_item import OrderItem


class MenuItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "menu_items"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    station_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("stations.id"), nullable=False)
    prep_minutes: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    station: Mapped["Station"] = relationship("Station", back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")
