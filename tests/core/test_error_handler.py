from flask import abort
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from flaskr.core.error_handler import ErrorHandler
from tests.base import BaseTestCase

SECRET_DETAIL = "SECRET-INTERNAL-DETAIL"


class FakeDiag:
    message_detail = f"Key (email)=({SECRET_DETAIL}) already exists."


class FakeUniqueViolation(Exception):
    pgcode = "23505"
    diag = FakeDiag()


class FakeForeignKeyViolation(Exception):
    pgcode = "23503"
    diag = None


def raise_unique_violation():
    raise IntegrityError("INSERT ...", {}, FakeUniqueViolation(SECRET_DETAIL))


def raise_foreign_key_violation():
    raise IntegrityError("INSERT ...", {}, FakeForeignKeyViolation(SECRET_DETAIL))


def raise_data_error():
    raise DataError("SELECT ...", {}, Exception(SECRET_DETAIL))


def raise_operational_error():
    raise OperationalError("SELECT ...", {}, Exception(SECRET_DETAIL))


def raise_unexpected_error():
    raise RuntimeError(SECRET_DETAIL)


def raise_abort():
    abort(409, description="Order is already preparation")


def get_only():
    return "ok"


class TestErrorHandler(BaseTestCase):
    domain_class = ErrorHandler

    def setup_case(self):
        routes = {
            "/_test/unique": raise_unique_violation,
            "/_test/foreign-key": raise_foreign_key_violation,
            "/_test/data-error": raise_data_error,
            "/_test/operational-error": raise_operational_error,
            "/_test/unexpected": raise_unexpected_error,
            "/_test/abort": raise_abort,
            "/_test/get-only": get_only,
        }
        for rule, view in routes.items():
            self.app.add_url_rule(rule, view_func=view, methods=["GET"])

    def assert_no_leak(self, res):
        assert SECRET_DETAIL not in res.get_data(as_text=True)

    def test_unique_violation_returns_409_with_field_name_only(self):
        res = self.client.get("/_test/unique")

        assert res.status_code == 409
        assert res.json == {
            "error": "Conflict",
            "message": "email already exists",
            "code": 409,
        }
        self.assert_no_leak(res)

    def test_other_integrity_error_returns_400(self):
        res = self.client.get("/_test/foreign-key")

        assert res.status_code == 400
        assert res.json["message"] == "Data violates a constraint"
        self.assert_no_leak(res)

    def test_data_error_returns_400(self):
        res = self.client.get("/_test/data-error")

        assert res.status_code == 400
        assert res.json == {
            "error": "Bad Request",
            "message": "Invalid value",
            "code": 400,
        }
        self.assert_no_leak(res)

    def test_database_error_returns_500_without_details(self):
        res = self.client.get("/_test/operational-error")

        assert res.status_code == 500
        assert res.json["message"] == "Unexpected error"
        self.assert_no_leak(res)

    def test_unexpected_error_returns_500_without_details(self):
        res = self.client.get("/_test/unexpected")

        assert res.status_code == 500
        assert res.json == {
            "error": "Internal Server Error",
            "message": "Unexpected error",
            "code": 500,
        }
        self.assert_no_leak(res)

    def test_unexpected_error_is_logged(self, caplog):
        self.client.get("/_test/unexpected")

        assert SECRET_DETAIL in caplog.text

    def test_abort_keeps_code_and_description(self):
        res = self.client.get("/_test/abort")

        assert res.status_code == 409
        assert res.json == {
            "error": "Conflict",
            "message": "Order is already preparation",
            "code": 409,
        }

    def test_unknown_route_returns_json_404(self):
        res = self.client.get("/_test/does-not-exist")

        assert res.status_code == 404
        assert res.is_json
        assert res.json["error"] == "Not Found"

    def test_method_not_allowed_keeps_allow_header(self):
        res = self.client.post("/_test/get-only")

        assert res.status_code == 405
        assert res.is_json
        assert "GET" in res.headers["Allow"]
