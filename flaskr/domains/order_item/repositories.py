from typing import List

from flask import abort
from sqlalchemy import delete, select

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.domains.order_item.models import OrderItem


class OrderItemRepository(BaseRepository[OrderItem]):
    model = OrderItem

    def add_bulk(self, order_id: int, items_data: list):
        for item in items_data:
            new_item = OrderItem(
                order_id=order_id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            db.session.add(new_item)

        db.session.flush()

    def get_by_order_id(self, order_id: int) -> List[OrderItem]:
        query = select(self.model).filter_by(order_id=order_id)
        return list(db.session.execute(query).scalars().all())

    def delete_item(self, order_id: int, product_id: int) -> bool:
        entity = db.session.get(self.model, (order_id, product_id))
        if entity:
            db.session.delete(entity)
            db.session.flush()
            return True
        return False

    def delete_all_by_order_id(self, order_id: int) -> bool:
        exists = (
            db.session.query(OrderItem).filter(OrderItem.order_id == order_id).first()
        )
        if not exists:
            abort(404, description="Order items for this order not found")

        stmt = delete(OrderItem).where(OrderItem.order_id == order_id)
        db.session.execute(stmt)
        return True

    def upsert_item(
        self, order_id: int, product_id: int, quantity: int, unit_price: float
    ) -> OrderItem:
        item = db.session.get(self.model, (order_id, product_id))

        if item:
            item.quantity = quantity
        else:
            item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
            )
            db.session.add(item)

        db.session.flush()
        return item
