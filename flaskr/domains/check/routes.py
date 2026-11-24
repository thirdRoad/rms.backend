from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.check.services import CheckService
from flaskr.domains.check.validators import (
    CheckCreateValidator,
    CheckFilterValidator,
    CheckSortValidator,
    CheckUpdateValidator,
)

from . import bp


class CheckListAPI(BaseRoutes):
    service = CheckService()
    validator = CheckCreateValidator()
    filter_validator = CheckFilterValidator()
    sort_validator = CheckSortValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self):  # List checks with their totals, filtered by query params
        checks_data = self.service.list_items(
            filters=self.get_filters(), sort=self.get_sorting()
        )
        return self.format_plural_response(data=checks_data)

    @role_required("admin", "service_staff")
    def post(self):  # Add a product to the table's open check, open one if needed
        data = self.validator.validate_data(request.get_json())
        response, is_new = self.service.add_product(data=data)
        return self.format_response(data=response), 201 if is_new else 200


class CheckDetailAPI(BaseRoutes):
    service = CheckService()
    validator = CheckUpdateValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, check_id: int):  # Get check with its products and total
        check = self.service.get_by_id(item_id=check_id)
        return self.format_response(data=check)

    @role_required("admin", "service_staff")
    def patch(self, check_id: int):  # Update quantity of a direct product, 0 removes
        data = self.validator.validate_data(request.get_json())
        response = self.service.update_product(check_id=check_id, data=data)
        return self.format_response(data=response)


class CheckCloseAPI(BaseRoutes):
    service = CheckService()

    @role_required("admin", "service_staff")
    def post(self, check_id: int):  # Payment, no body
        response = self.service.close_check(check_id=check_id)
        return self.format_response(data=response)


class CheckCancelAPI(BaseRoutes):
    service = CheckService()

    @role_required("admin", "service_staff")
    def post(self, check_id: int):  # Cancel, no body
        response = self.service.cancel_check(check_id=check_id)
        return self.format_response(data=response)


bp.add_url_rule(
    "/", view_func=CheckListAPI.as_view("check_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:check_id>",
    view_func=CheckDetailAPI.as_view("check_detail_api"),
    methods=["GET", "PATCH"],
)

bp.add_url_rule(
    "/<int:check_id>/close",
    view_func=CheckCloseAPI.as_view("check_close_api"),
    methods=["POST"],
)

bp.add_url_rule(
    "/<int:check_id>/cancel",
    view_func=CheckCancelAPI.as_view("check_cancel_api"),
    methods=["POST"],
)
