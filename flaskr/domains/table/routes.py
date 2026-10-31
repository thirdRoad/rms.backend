from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.table.services import TableService
from flaskr.domains.table.validators import TableUpdateValidator

from . import bp


class TableListAPI(BaseRoutes):
    service = TableService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self):  # List all tables
        users_data = self.service.list_items()
        return self.format_plural_response(data=users_data)

    @role_required("admin")
    def post(self):  # Added table
        new_table = self.service.create_new_table()

        response = self.format_response(data=new_table.serialize)
        return response, 201


class TableDetailAPI(BaseRoutes):
    service = TableService()

    @role_required("admin", "service_staff", "kitchen_staff")
    def get(self, table_id: int):  # Get table by id
        table = self.service.get_by_id(item_id=table_id)
        return self.format_response(data=table)

    @role_required("admin", "service_staff")
    def patch(self, table_id: int):  # Update table information
        data = TableUpdateValidator().get_table_status(request.get_json())
        response = self.service.update_item(item_id=table_id, data=data)

        return self.format_response(data=response)

    @role_required("admin")
    def delete(self, table_id: int):  # Delete table
        self.service.delete_item(item_id=table_id)
        return "", 204


bp.add_url_rule(
    "/", view_func=TableListAPI.as_view("table_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:table_id>",
    view_func=TableDetailAPI.as_view("table_detail_api"),
    methods=["GET", "PATCH", "DELETE"],
)
