from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.order.services import OrderService
from flaskr.domains.order.validators import OrderCreateValidator, OrderUpdateValidator

from . import bp


class OrderListAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self):  # List all order id and created_at
        order_data = self.service.list_items()
        return self.format_plural_response(data=order_data)

    @role_required("admin", "service_staff")
    def post(self):  # Post order with products
        data = OrderCreateValidator().validate_data(request.get_json())
        response = self.service.create_new_order(data=data)
        return self.format_response(data=response), 201


class OrderItemsAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, order_id: int):  # get order details
        response = self.service.get_by_order_id_orderdetails(order_id=order_id)
        return self.format_plural_response(data=response)


class OrderUpdateAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff")
    def patch(self, order_id: int, product_id: int):  # Update order products
        data = OrderUpdateValidator().validate_data(request.get_json())
        quantity = data["quantity"]
        response = self.service.update_order_product(
            order_id=order_id, product_id=product_id, quantity=quantity
        )

        return self.format_response(data=response)


class OrderDetailAPI(BaseRoutes):
    service = OrderService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, order_id: int):  # get order and user by id
        order = self.service.get_by_id(item_id=order_id)
        return self.format_response(data=order)

    @role_required("admin", "service_staff")
    def delete(self, order_id: int):  # Delete order products
        self.service.delete_order_products(item_id=order_id)
        return "", 204


bp.add_url_rule(
    "/", view_func=OrderListAPI.as_view("order_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:order_id>",
    view_func=OrderDetailAPI.as_view("order_detail_api"),
    methods=["GET", "DELETE"],
)
bp.add_url_rule(
    "/<int:order_id>/items/<int:product_id>",
    view_func=OrderUpdateAPI.as_view("order_update_api"),
    methods=["PATCH"],
)


bp.add_url_rule(
    "/<int:order_id>/items",
    view_func=OrderItemsAPI.as_view("order_items_api"),
    methods=["GET"],
)
