from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flaskr.core.base.models import BaseModel
from flaskr.core.utils import to_iso, utc_now

if TYPE_CHECKING:
    from flaskr.domains.order.models import Order


class TableStatus(Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"


class Table(BaseModel):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[TableStatus] = mapped_column(
        SQLEnum(TableStatus), default=TableStatus.AVAILABLE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="table")

    @property
    def serialize(self) -> Dict:
        return {
            "id": self.id,
            "status": (
                self.status.value if hasattr(self.status, "value") else self.status
            ),
            "created_at": to_iso(self.created_at),
            "last_updated": (to_iso(self.last_updated)),
        }
