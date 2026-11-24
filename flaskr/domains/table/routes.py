from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.table.models import TableStatus
from flaskr.domains.table.services import TableService
from flaskr.domains.table.validators import (
    TableCreateValidator,
    TableFilterValidator,
    TableSortValidator,
    TableUpdateValidator,
)

from . import bp


class TableListAPI(BaseRoutes):
    service = TableService()
    validator = TableCreateValidator()
    filter_validator = TableFilterValidator()
    sort_validator = TableSortValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self):  # List tables, filtered and sorted by query params
        tables_data = self.service.list_items(
            filters=self.get_filters(), sort=self.get_sorting()
        )
        return self.format_plural_response(data=tables_data)

    @role_required("admin")
    def post(self):  # Added table
        data = self.validator.validate_data(data=request.get_json())
        new_table = self.service.create_new_table(data=data)

        response = self.format_response(data=new_table.serialize)
        return response, 201


class TableDetailAPI(BaseRoutes):
    service = TableService()
    validator = TableUpdateValidator()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, table_id: int):  # Get table by id
        table = self.service.get_by_id(item_id=table_id)
        return self.format_response(data=table)

    @role_required("admin", "service_staff")
    def patch(self, table_id: int):  # Update table information
        data = self.validator.validate_data(request.get_json())
        response = self.service.update_item(item_id=table_id, data=data)

        return self.format_response(data=response)

    @role_required("admin")
    def delete(self, table_id: int):  # Delete table
        self.service.delete_item(item_id=table_id)
        return "", 204


class TableStatusAPI(BaseRoutes):
    service = TableService()

    @role_required("admin", "service_staff")
    def post(self, table_id: int, status: TableStatus):  # Change status, no body
        response = self.service.update_item(item_id=table_id, data={"status": status})
        return self.format_response(data=response)


bp.add_url_rule(
    "/", view_func=TableListAPI.as_view("table_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:table_id>",
    view_func=TableDetailAPI.as_view("table_detail_api"),
    methods=["GET", "PATCH", "DELETE"],
)

bp.add_url_rule(
    "/<int:table_id>/available",
    view_func=TableStatusAPI.as_view("table_available_api"),
    methods=["POST"],
    defaults={"status": TableStatus.AVAILABLE},
)

bp.add_url_rule(
    "/<int:table_id>/reserved",
    view_func=TableStatusAPI.as_view("table_reserved_api"),
    methods=["POST"],
    defaults={"status": TableStatus.RESERVED},
)

bp.add_url_rule(
    "/<int:table_id>/occupied",
    view_func=TableStatusAPI.as_view("table_occupied_api"),
    methods=["POST"],
    defaults={"status": TableStatus.OCCUPIED},
)
