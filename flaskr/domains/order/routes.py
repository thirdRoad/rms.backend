from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.order.models import OrderStatus
from flaskr.domains.order.services import OrderService
from flaskr.domains.order.validators import OrderCreateValidator, OrderUpdateValidator

from . import bp


class OrderListAPI(BaseRoutes):
    service = OrderService()
    validator = OrderCreateValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self):  # List all order id and created_at
        order_data = self.service.list_items()
        return self.format_plural_response(data=order_data)

    @role_required("admin", "service_staff")
    def post(self):  # Post order with products
        data = self.validator.validate_data(request.get_json())
        response = self.service.create_new_order(data=data)
        return self.format_response(data=response), 201


class OrderDetailAPI(BaseRoutes):
    service = OrderService()
    validator = OrderUpdateValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, order_id: int):  # get order and user by id
        order = self.service.get_by_id(item_id=order_id)
        return self.format_response(data=order)

    @role_required("admin", "service_staff")
    def patch(self, order_id: int):  # Replace order items with the given list
        data = self.validator.validate_data(request.get_json())
        response = self.service.update_order_items(
            order_id=order_id, items=data["items"]
        )
        return self.format_plural_response(data=response)

    @role_required("admin")
    def delete(self, order_id: int):  # Delete the order with its items
        self.service.delete_item(item_id=order_id)
        return "", 204


class OrderStatusAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def post(self, order_id: int, status: str):  # Change status, no body
        response = self.service.update_order_status(order_id=order_id, status=status)
        return self.format_response(data=response)


class OrderItemsAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, order_id: int):  # get order details
        response = self.service.get_order_items(order_id=order_id)
        return self.format_plural_response(data=response)

    @role_required("admin", "service_staff")
    def delete(self, order_id: int):  # Delete all items of the order
        self.service.delete_order_products(item_id=order_id)
        return "", 204


bp.add_url_rule(
    "/", view_func=OrderListAPI.as_view("order_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:order_id>",
    view_func=OrderDetailAPI.as_view("order_detail_api"),
    methods=["GET", "PATCH", "DELETE"],
)

bp.add_url_rule(
    "/<int:order_id>/preparation",
    view_func=OrderStatusAPI.as_view("order_preparation_api"),
    methods=["POST"],
    defaults={"status": OrderStatus.PREPARATION.value},
)

bp.add_url_rule(
    "/<int:order_id>/done",
    view_func=OrderStatusAPI.as_view("order_done_api"),
    methods=["POST"],
    defaults={"status": OrderStatus.DONE.value},
)

bp.add_url_rule(
    "/<int:order_id>/cancelled",
    view_func=OrderStatusAPI.as_view("order_cancelled_api"),
    methods=["POST"],
    defaults={"status": OrderStatus.CANCELLED.value},
)


bp.add_url_rule(
    "/<int:order_id>/items",
    view_func=OrderItemsAPI.as_view("order_items_api"),
    methods=["GET", "DELETE"],
)
