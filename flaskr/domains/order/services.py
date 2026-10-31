from typing import Any, Dict, List

from flask import abort

from flaskr.core.base.services import BaseService
from flaskr.core.utils import to_iso
from flaskr.domains.order.repositories import OrderRepository
from flaskr.domains.order_item.repositories import OrderItemRepository
from flaskr.domains.product.repositories import ProductRepository
from flaskr.domains.table.repositories import TableRepository
from flaskr.domains.user.repositories import UserRepository


class OrderService(BaseService):
    repository: OrderRepository
    repository = OrderRepository()
    order_item_repo = OrderItemRepository()
    product_repo = ProductRepository()
    table_repo = TableRepository()
    user_repo = UserRepository()

    def get_by_id(self, item_id: int) -> Dict | None:
        order = self.repository.get_by_id(item_id=item_id)

        if order is None:
            abort(404, description="Order not found")

        response = order.serialize
        response["user"] = {
            "id": order.user.id,
            "username": order.user.username,
            "email": order.user.email,
            "created_at": to_iso(order.user.created_at),
            "display_name": order.user.display_name,
        }
        return response

    def products_is_exists(self, items: List[Dict[str, Any]]) -> bool:
        product_ids = [item["product_id"] for item in items]

        duplicates = sorted({pid for pid in product_ids if product_ids.count(pid) > 1})
        if duplicates:
            abort(400, description=f"Duplicate product_id in items: {duplicates}")

        missing = [
            pid for pid in product_ids if self.product_repo.get_by_id(pid) is None
        ]
        if missing:
            abort(404, description=f"Product not found: {missing}")
        return True

    def get_order_items(self, order_id: int) -> List[Dict[str, Any]]:
        if self.repository.get_by_id(order_id) is None:
            abort(404, description="Order not found")

        items = self.order_item_repo.get_by_order_id(order_id)
        if not items:
            abort(404, description="Order has no items")

        return [item.serialize for item in items]

    def create_new_order(self, data: Dict[str, Any]) -> Dict[str, Any]:

        user = self.user_repo.get_by_id(data["user_id"])

        if user is None:
            abort(404, description="User not found")

        table = self.table_repo.get_by_id(data["table_id"])

        if table is None:
            abort(404, description="Table not found")

        self.products_is_exists(data["items"])

        order = self.repository.add(data=data)
        return order.serialize

    # update order detail products and quantity
    def update_order_product(
        self, order_id: int, product_id: int, quantity: int
    ) -> Dict[str, Any]:
        order = self.repository.get_by_id(order_id)
        if order is None:
            abort(404, description="Order not found")

        product = self.product_repo.get_by_id(product_id)
        if product is None:
            abort(404, description="Product not found")

        item = self.repository.update_order_product(
            order_id=order_id, product_id=product_id, quantity=quantity
        )
        return item.serialize

    # delete order details fonks
    def delete_order_products(self, item_id: int) -> bool:
        order = self.repository.get_by_id(item_id)
        if order is None:
            abort(404, description="Order is not found")
        return self.repository.delete_order_products(order_id=item_id)
