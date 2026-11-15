from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError
from typing_extensions import override

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.domains.order.models import Order
from flaskr.domains.order_item.models import OrderItem
from flaskr.domains.order_item.repositories import OrderItemRepository
from flaskr.domains.product.repositories import ProductRepository


class OrderRepository(BaseRepository[Order]):
    model = Order
    product_repo = ProductRepository()
    order_item_repo = OrderItemRepository()

    @override
    def add(self, data: Dict[str, Any]) -> Order:
        order = Order(
            user_id=data["user_id"],
            table_id=data["table_id"],
        )

        db.session.add(order)
        db.session.flush()

        details_to_add = []
        for item in data["items"]:
            product = self.product_repo.get_by_id(item["product_id"])
            if product:
                details_to_add.append(
                    {
                        "product_id": product.id,
                        "quantity": item["quantity"],
                        "unit_price": product.price,
                    }
                )

        self.order_item_repo.add_bulk(order.id, details_to_add)

        db.session.commit()

        return order

    def delete_order_products(
        self, order_id: int
    ) -> bool:  # delete order details fonks
        try:
            result = self.order_item_repo.delete_all_by_order_id(order_id=order_id)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            raise e

    def replace_order_items(
        self, order_id: int, items: List[Dict[str, Any]]
    ) -> List[OrderItem]:
        keep_ids = {item["product_id"] for item in items}
        try:
            for existing in self.order_item_repo.get_by_order_id(order_id):
                if existing.product_id not in keep_ids:
                    db.session.delete(existing)

            result = []
            for item in items:
                product = self.product_repo.get_by_id(item["product_id"])
                result.append(
                    self.order_item_repo.upsert_item(
                        order_id=order_id,
                        product_id=product.id,
                        quantity=item["quantity"],
                        unit_price=product.price,
                    )
                )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        return result
