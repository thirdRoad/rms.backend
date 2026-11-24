from typing import Any, Dict, List

from flask import abort

from flaskr.core.base.services import BaseService
from flaskr.core.errors import not_found
from flaskr.domains.order.models import OrderStatus
from flaskr.domains.order.repositories import OrderRepository
from flaskr.domains.order_item.repositories import OrderItemRepository
from flaskr.domains.product.repositories import ProductRepository
from flaskr.domains.table.repositories import TableRepository
from flaskr.domains.user.repositories import UserRepository


class OrderService(BaseService):
    repository: OrderRepository
    repository = OrderRepository()
    domain = "Order"
    order_item_repo = OrderItemRepository()
    product_repo = ProductRepository()
    table_repo = TableRepository()
    user_repo = UserRepository()

    def update_order_status(self, order_id: int, status: str) -> Dict[str, Any]:
        order = self.get_or_404(order_id)

        new_status = OrderStatus(status)
        if order.status == new_status:
            abort(409, description=f"Order is already {new_status.value}")

        self.repository.update(item_id=order_id, data={"status": new_status})
        return self.get_by_id(item_id=order_id)

    def products_is_exists(self, items: List[Dict[str, Any]]) -> bool:
        product_ids = [item["product_id"] for item in items]

        duplicates = sorted({pid for pid in product_ids if product_ids.count(pid) > 1})
        if duplicates:
            abort(400, description=f"Duplicate product_id in items: {duplicates}")

        missing = [
            pid for pid in product_ids if self.product_repo.get_by_id(pid) is None
        ]
        if missing:
            not_found("Product", missing)
        return True

    def get_order_items(self, order_id: int) -> List[Dict[str, Any]]:
        self.get_or_404(order_id)
        items = self.order_item_repo.get_by_order_id(order_id)
        return [item.serialize for item in items]  # empty order -> []

    def create_new_order(self, data: Dict[str, Any]) -> Dict[str, Any]:

        if self.user_repo.get_by_id(data["user_id"]) is None:
            not_found("User")

        if self.table_repo.get_by_id(data["table_id"]) is None:
            not_found("Table")

        self.products_is_exists(data["items"])

        order = self.repository.add(data=data)
        return order.serialize

    # body is the final item list: update existing, add new, remove the missing ones
    def update_order_items(
        self, order_id: int, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        self.get_or_404(order_id)
        self.products_is_exists(items)

        self.repository.replace_order_items(order_id=order_id, items=items)
        return self.get_order_items(order_id=order_id)

    # delete order details fonks
    def delete_order_products(self, item_id: int) -> bool:
        self.get_or_404(item_id)
        return self.repository.delete_order_products(order_id=item_id)
