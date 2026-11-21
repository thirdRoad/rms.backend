from typing import Any, Dict, List

from flask import Response, jsonify, request
from flask.views import MethodView

from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseQueryValidator,
    BaseSortValidator,
)
from flaskr.core.utils import to_iso, utc_now


class BaseRoutes(MethodView):
    # Set in a domain route to enable the feature; None = disabled.
    filter_validator: None | BaseFilterValidator = None
    sort_validator: None | BaseSortValidator = None

    @staticmethod
    def get_query_params(validator: None | BaseQueryValidator) -> Dict[str, Any]:
        if validator is None:
            return {}
        return validator.validate_query(request.args)

    def get_filters(self) -> Dict[str, Any]:
        return self.get_query_params(self.filter_validator)

    def get_sorting(self) -> List[str]:
        return self.get_query_params(self.sort_validator).get("sort", [])

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
