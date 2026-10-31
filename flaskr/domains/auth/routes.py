from typing import Any, Dict

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from flaskr.core.base.routes import BaseRoutes
from flaskr.core.decorators import role_required
from flaskr.core.utils import to_iso, utc_now
from flaskr.domains.auth.services import AuthService
from flaskr.domains.auth.validators import AuthLoginValidator
from flaskr.domains.user.services import UserService

from . import bp


class BaseAuthAPI(BaseRoutes):
    service: AuthService = AuthService()

    @staticmethod
    def format_token_response(data: Dict[str, Any]) -> Response:
        final_data = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
        }
        response = {
            "server_time": to_iso(utc_now()),
            "data": final_data,
        }
        return jsonify(response)

    @staticmethod
    def format_logout_response(data: Dict[str, Any]) -> Response:
        response = {
            "server_time": to_iso(utc_now()),
            "data": data,
        }
        return jsonify(response)


class AuthLoginAPI(BaseAuthAPI):
    service: AuthService = AuthService()

    def post(self):  # Verify user and generate tokens
        data = AuthLoginValidator().validate_data(data=request.get_json())
        tokens = self.service.verify_user(
            username=data["username"], password=data["password"]
        )
        return self.format_token_response(data=tokens)


class AuthLogoutAPI(BaseAuthAPI):
    service: AuthService = AuthService()

    @jwt_required()
    def post(self):  # Blacklist tokens and logout
        self.service.logout()
        return self.format_logout_response(data={"msg": "Successfully logged out"})


class AuthMeAPI(BaseAuthAPI):
    service: UserService = UserService()

    @role_required("admin", "service_staff", "kitchen_staff")
    @jwt_required()
    def get(self):  # Get current user profile data by JWT identity
        user_id = int(get_jwt_identity())
        user_data = self.service.get_by_id(item_id=user_id)
        return self.format_response(data=user_data)


bp.add_url_rule(
    "/login", view_func=AuthLoginAPI.as_view("auth_login_api"), methods=["POST"]
)
bp.add_url_rule(
    "/logout", view_func=AuthLogoutAPI.as_view("auth_logout_api"), methods=["POST"]
)
bp.add_url_rule("/me", view_func=AuthMeAPI.as_view("auth_me_api"), methods=["GET"])
