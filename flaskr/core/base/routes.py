from typing import Any

from flask import Response, jsonify
from flask.views import MethodView

from flaskr.core.utils import to_iso, utc_now


class BaseRoutes(MethodView):
    @staticmethod
    def format_response(data: Any, pagination: bool = False) -> Response:
        response = {
            "server_time": to_iso(utc_now()),
            "data": data,
        }

        if pagination:
            pass

        return jsonify(response)

    @staticmethod
    def format_plural_response(data: Any, pagination: bool = False) -> Response:
        response = {
            "server_time": to_iso(utc_now()),
            "count": len(data),
            "data": data,
        }

        if pagination:
            pass

        return jsonify(response)
