from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.menu_item import MenuItem
    from app.models.order_item import OrderItem


class Station(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "stations"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    active_cooks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    menu_items: Mapped[List["MenuItem"]] = relationship("MenuItem", back_populates="station")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="station")
