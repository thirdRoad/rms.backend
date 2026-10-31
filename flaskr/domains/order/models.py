from datetime import datetime
from typing import TYPE_CHECKING, Dict

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, relationship

from flaskr.core.base.models import BaseModel, mapped_column, mapped_foreign_key
from flaskr.core.utils import to_iso, utc_now

if TYPE_CHECKING:
    from flaskr.domains.order_detail.models import OrderDetail
    from flaskr.domains.table.models import Table
    from flaskr.domains.user.models import User


class Order(BaseModel):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    user_id: Mapped[int] = mapped_foreign_key("users.id")
    user: Mapped["User"] = relationship(back_populates="orders")
    table_id: Mapped[int] = mapped_foreign_key("tables.id")
    table: Mapped["Table"] = relationship(back_populates="orders")

    order_details: Mapped[list["OrderDetail"]] = relationship(
        "OrderDetail", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def serialize(self) -> Dict:
        return {
            "id": self.id,
            "created_at": to_iso(self.created_at),
        }
