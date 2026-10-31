from typing import Any, Dict

from typing_extensions import override

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.domains.order.models import Order
from flaskr.domains.order_detail.models import OrderDetail
from flaskr.domains.order_detail.repositories import OrderDetailRepository
from flaskr.domains.product.repositories import ProductRepository


class OrderRepository(BaseRepository[Order]):
    model = Order
    product_repo = ProductRepository()
    order_detail_repo = OrderDetailRepository()

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

        self.order_detail_repo.add_bulk(order.id, details_to_add)

        db.session.commit()

        return order

    def delete_order_products(
        self, order_id: int
    ) -> bool:  # delete order details fonks
        try:
            result = self.order_detail_repo.delete_all_by_order_id(order_id=order_id)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            raise e

        # update order detail products and quantity

    def update_order_product(
        self, order_id: int, product_id: int, quantity: int
    ) -> OrderDetail:
        product = self.product_repo.get_by_id(product_id)
        item = self.order_detail_repo.upsert_item(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
        )
        db.session.commit()
        return item
