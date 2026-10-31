from flask import request

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.domains.user.services import UserService
from flaskr.domains.user.validators import UserCreateValidator, UserUpdateValidator

from . import bp


class UserListAPI(BaseRoutes):
    service = UserService()
    validator = UserCreateValidator()

    @role_required("admin")
    def get(self):  # Return all users
        users_data = self.service.list_items()
        return self.format_plural_response(data=users_data)

    @role_required("admin")
    def post(self):  # Post user
        data = self.validator.validate_data(request.get_json())
        new_user = self.service.create_new_user(data=data)

        response = self.format_response(data=new_user)
        return response, 201


class UserDetailAPI(BaseRoutes):
    service = UserService()
    validator = UserUpdateValidator()

    @role_required("admin")
    def get(self, user_id: int):  # Get user by id
        user = self.service.get_by_id(item_id=user_id)
        return self.format_response(data=user)

    @role_required("admin")
    def patch(self, user_id: int):  # update user information
        data = self.validator.validate_data(request.get_json())
        response = self.service.update_item(item_id=user_id, data=data)
        return self.format_response(data=response)

    @role_required("admin")
    def delete(self, user_id: int):  # delete user
        self.service.delete_item(item_id=user_id)
        return "", 204


bp.add_url_rule(
    "/", view_func=UserListAPI.as_view("user_list_api"), methods=["GET", "POST"]
)

bp.add_url_rule(
    "/<int:user_id>",
    view_func=UserDetailAPI.as_view("user_detail_api"),
    methods=["GET", "PATCH", "DELETE"],
)
