from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flaskr.core.base.models import BaseModel
from flaskr.core.utils import to_iso, utc_now

if TYPE_CHECKING:
    from flaskr.domains.product.models import Product

"""
if TYPE_CHECKING:
    from flaskr.domains.product import Product
"""


class Category(BaseModel):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    products: Mapped[List["Product"]] = relationship(back_populates="category")

    @property
    def serialize(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": to_iso(self.created_at),
        }
