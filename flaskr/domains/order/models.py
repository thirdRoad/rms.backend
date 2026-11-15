from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, relationship

from flaskr.core.base.models import BaseModel, mapped_column, mapped_foreign_key
from flaskr.core.utils import to_iso, utc_now

if TYPE_CHECKING:
    from flaskr.domains.order_item.models import OrderItem
    from flaskr.domains.table.models import Table
    from flaskr.domains.user.models import User


class OrderStatus(Enum):
    PREPARATION = "preparation"
    DONE = "done"
    CANCELLED = "cancelled"


class Order(BaseModel):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PREPARATION,
        server_default=OrderStatus.PREPARATION.name,  # for existing rows (NOT NULL)
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    user_id: Mapped[int] = mapped_foreign_key("users.id")
    user: Mapped["User"] = relationship(back_populates="orders")
    table_id: Mapped[int] = mapped_foreign_key("tables.id")
    table: Mapped["Table"] = relationship(back_populates="orders")

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def serialize(self) -> Dict:
        return {
            "id": self.id,
            "status": self.status.value if self.status else None,
            "created_at": to_iso(self.created_at),
        }
