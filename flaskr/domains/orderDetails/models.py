from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flaskr.core.base.model import BaseModel

if TYPE_CHECKING:
    from flaskr.domains.orders.models import Order
    from flaskr.domains.product.models import Product


class OrderDetail(BaseModel):
    __tablename__ = "order_details"

    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), primary_key=True
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship("Order", back_populates="order_details")
    product: Mapped["Product"] = relationship(back_populates="order_details")

    @property
    def serialize(self) -> Dict:
        return {
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "created_at": self.created_at.isoformat(),
        }
