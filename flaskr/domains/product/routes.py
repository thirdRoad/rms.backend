from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.product.services import ProductService
from flaskr.domains.product.validators import (
    ProductCreateValidator,
    ProductUpdateValidator,
)

from . import bp


class ProductListAPI(BaseRoutes):
    service = ProductService()
    validator = ProductCreateValidator()

    @role_required("admin", "service_staff")
    def get(self):
        search_value = request.args.get("name")
        category_id = request.args.get("category")

        if search_value and category_id:
            name_search_products = self.service.search_by_product_name(
                value=search_value
            )
            filter_category_products = self.service.filter_by_category(
                category_id=category_id
            )
            id_set = {
                product["id"] for product in name_search_products if "id" in product
            }
            products = [
                product
                for product in filter_category_products
                if product.get("id") in id_set
            ]

        elif search_value:
            products = self.service.search_by_product_name(value=search_value)

        elif category_id:
            products = self.service.filter_by_category(category_id=category_id)

        else:
            products = self.service.list_items()

        return self.format_plural_response(data=products)

    @role_required("admin")
    def post(self):  # Post product
        data = self.validator.validate_data(request.get_json())
        new_product = self.service.create_new_product(data=data)

        response = self.format_response(data=new_product)
        return response, 201


class ProductDetailAPI(BaseRoutes):
    service = ProductService()
    validator = ProductUpdateValidator()

    @role_required("admin", "service_staff")
    def get(self, product_id: int):  # Get product by id
        product = self.service.get_by_id(item_id=product_id)
        return self.format_response(data=product)

    @role_required("admin")
    def patch(self, product_id: int):  # Update product information
        data = self.validator.validate_data(request.get_json())
        response = self.service.update_item(item_id=product_id, data=data)
        return self.format_response(data=response)

    @role_required("admin")
    def delete(self, product_id: int):  # Delete product
        self.service.delete_item(item_id=product_id)
        return "", 204


bp.add_url_rule(
    "/",
    view_func=ProductListAPI.as_view("product_list"),
    methods=["GET", "POST"],
)

bp.add_url_rule(
    "/<int:product_id>",
    view_func=ProductDetailAPI.as_view("product_detail"),
    methods=["GET", "PATCH", "DELETE"],
)
