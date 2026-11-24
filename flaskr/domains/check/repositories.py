from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import SQLAlchemyError

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.domains.check.models import Check, CheckProduct, CheckStatus
from flaskr.domains.order.models import Order, OrderStatus
from flaskr.domains.order_item.models import OrderItem


def start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class CheckRepository(BaseRepository[Check]):
    model = Check

    @staticmethod
    def activity_time() -> ColumnElement[datetime]:
        # open checks are dated by created_at, closed ones by closed_at
        return func.coalesce(Check.closed_at, Check.created_at)

    def filter_start(self, value: date) -> ColumnElement[bool]:
        return self.activity_time() >= start_of_day(value)

    def filter_end(self, value: date) -> ColumnElement[bool]:  # end day included
        return self.activity_time() < start_of_day(value + timedelta(days=1))

    def get_open_by_table(self, table_id: int) -> Optional[Check]:
        query = select(Check).filter_by(table_id=table_id, status=CheckStatus.OPEN)
        return db.session.scalars(query).one_or_none()

    def get_unbilled_order_items(self, table_id: int) -> List[OrderItem]:
        # orders already copied into a closed check must not be billed again
        billed_order_ids = select(CheckProduct.order_id).where(
            CheckProduct.order_id.is_not(None)
        )
        query = (
            select(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.table_id == table_id,
                Order.status != OrderStatus.CANCELLED,
                Order.id.not_in(billed_order_ids),
            )
            .order_by(Order.id, OrderItem.product_id)
        )
        return list(db.session.scalars(query).all())

    def save(self, entity: Check) -> Check:
        db.session.add(entity)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        return entity
