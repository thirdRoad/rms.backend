from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.category import bp
from flaskr.domains.category.services import CategoryService
from flaskr.domains.category.validators import CategoryValidator


class CategoryListAPI(BaseRoutes):
    service = CategoryService()
    validator = CategoryValidator()

    @role_required("admin", "service_staff")
    def get(self):  # list all category
        category_data = self.service.list_items()
        return self.format_plural_response(data=category_data)

    @role_required("admin")
    def post(self):  # post category
        data = self.validator.validate_data(request.get_json())
        new_category = self.service.create_new_category(data=data)

        response = self.format_response(data=new_category)
        return response, 201


class CategoryDetailsAPI(BaseRoutes):
    service = CategoryService()
    validator = CategoryValidator()

    @role_required("admin", "service_staff")
    def get(self, category_id: int):  # get category by id
        category = self.service.get_by_id(category_id)
        return self.format_response(data=category)

    @role_required("admin")
    def patch(self, category_id: int):  # update category
        data = self.validator.validate_data(request.get_json())

        response = self.service.update_item(item_id=category_id, data=data)
        return self.format_response(data=response)

    @role_required("admin")
    def delete(self, category_id: int):  # delete category
        self.service.delete_item(item_id=category_id)
        return "", 204


bp.add_url_rule(
    "/", view_func=CategoryListAPI.as_view("category_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:category_id>/",
    view_func=CategoryDetailsAPI.as_view("category_details_api"),
    methods=["GET", "PATCH", "DELETE"],
)
