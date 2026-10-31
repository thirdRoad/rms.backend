from typing import Any, Dict, List

from flask import abort

from flaskr.core.base.services import BaseService
from flaskr.domains.order.repositories import OrderRepository
from flaskr.domains.order_detail.models import OrderDetail
from flaskr.domains.order_detail.repositories import OrderDetailRepository
from flaskr.domains.product.repositories import ProductRepository
from flaskr.domains.table.repositories import TableRepository
from flaskr.domains.user.repositories import UserRepository


class OrderService(BaseService):
    repository: OrderRepository
    repository = OrderRepository()
    order_detail_repo = OrderDetailRepository()
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
            "created_at": order.user.created_at,
            "display_name": order.user.display_name,
        }
        return response

    def get_by_order_id_orderdetails(self, order_id: int) -> List[OrderDetail]:
        orders = self.order_detail_repo.get_by_order_id(order_id)

        if not orders:
            abort(404, description="Order not found")

        response = []

        for order in orders:
            response.append(order.serialize)

        return response

    def create_new_order(self, data: Dict[str, Any]) -> Dict[str, Any]:

        user = self.user_repo.get_by_id(data["user_id"])

        if user is None:
            abort(404, description="User not found")

        table = self.table_repo.get_by_id(data["table_id"])

        if table is None:
            abort(404, description="Table not found")

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
