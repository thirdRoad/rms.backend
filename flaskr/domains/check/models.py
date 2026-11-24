from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flaskr.core.base.models import BaseModel, mapped_foreign_key
from flaskr.core.utils import to_iso, utc_now

if TYPE_CHECKING:
    from flaskr.domains.table.models import Table


class CheckStatus(Enum):
    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"


class CheckProductSource(Enum):
    CHECK = "check"  # added directly to the check, never sent to the kitchen
    ORDER = "order"  # copied from an order when the check is closed


class Check(BaseModel):
    __tablename__ = "checks"
    __table_args__ = (  # at most one open check per table
        Index(
            "uq_checks_open_table_id",
            "table_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
            sqlite_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[CheckStatus] = mapped_column(
        SQLEnum(CheckStatus), default=CheckStatus.OPEN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=True)  # set on close

    table_id: Mapped[int] = mapped_foreign_key("tables.id")
    table: Mapped["Table"] = relationship("Table")

    products: Mapped[list["CheckProduct"]] = relationship(
        back_populates="check",
        cascade="all, delete-orphan",
        order_by="CheckProduct.id",
    )

    @property
    def serialize(self) -> Dict:
        return {
            "id": self.id,
            "table_id": self.table_id,
            "status": self.status.value,
            "created_at": to_iso(self.created_at),
            "closed_at": to_iso(self.closed_at),
            "total": self.total,
        }


class CheckProduct(BaseModel):
    __tablename__ = "check_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[CheckProductSource] = mapped_column(
        SQLEnum(CheckProductSource), nullable=False
    )
    order_id: Mapped[int] = mapped_column(Integer, nullable=True)

    check_id: Mapped[int] = mapped_foreign_key("checks.id")
    check: Mapped["Check"] = relationship(back_populates="products")
    product_id: Mapped[int] = mapped_foreign_key("product.id")

    @property
    def serialize(self) -> Dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "source": self.source.value,
            "order_id": self.order_id,
        }
