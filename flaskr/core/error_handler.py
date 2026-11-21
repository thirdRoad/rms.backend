import re

from flask import Flask, Response, current_app, jsonify
from marshmallow import ValidationError
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from flaskr.core.extensions import db, jwt

PG_UNIQUE_VIOLATION = "23505"
UNIQUE_KEY_PATTERN = re.compile(r"Key \((\w+)\)")


def error_response(code: int, error: str, message: object) -> tuple[Response, int]:
    return jsonify({"error": error, "message": message, "code": code}), code


def is_unique_violation(e: IntegrityError) -> bool:
    if getattr(e.orig, "pgcode", None) == PG_UNIQUE_VIOLATION:
        return True
    return "UNIQUE constraint failed" in str(e.orig)  # SQLite (tests)


def conflicting_field(e: IntegrityError) -> None | str:
    # "Key (email)=(a@b.com) already exists." -> "email"
    detail = getattr(getattr(e.orig, "diag", None), "message_detail", None) or ""
    match = UNIQUE_KEY_PATTERN.search(detail)
    return match.group(1) if match else None


def unauthorized(message: str) -> tuple[Response, int]:
    return error_response(401, "Unauthorized", message)


class ErrorHandler:
    @staticmethod
    def init_app(app: Flask) -> None:
        ErrorHandler._register_app_handlers(app)
        ErrorHandler._register_jwt_handlers()

    @staticmethod
    def _register_jwt_handlers() -> None:
        # flask-jwt-extended registers its own error handlers on the app; these
        # loaders replace its default responses (raw library messages, 422 for
        # invalid tokens) with our format and fixed messages.
        @jwt.unauthorized_loader
        def missing_token(_reason: str):
            return unauthorized("Missing authorization token")

        @jwt.invalid_token_loader
        def invalid_token(_reason: str):
            return unauthorized("Invalid token")

        @jwt.expired_token_loader
        def expired_token(_header: dict, _payload: dict):
            return unauthorized("Token has expired")

        @jwt.revoked_token_loader
        def revoked_token(_header: dict, _payload: dict):
            return unauthorized("Token has been revoked")

        @jwt.needs_fresh_token_loader
        def needs_fresh_token(_header: dict, _payload: dict):
            return unauthorized("Fresh token required")

        @jwt.token_verification_failed_loader
        def token_verification_failed(_header: dict, _payload: dict):
            return unauthorized("Invalid token")

        @jwt.user_lookup_error_loader
        def user_lookup_error(_header: dict, _payload: dict):
            return unauthorized("Invalid token")

    @staticmethod
    def _register_app_handlers(app: Flask) -> None:
        @app.errorhandler(ValidationError)
        def handle_validation_error(e: ValidationError):
            return error_response(400, "Validation Error", e.messages)

        @app.errorhandler(IntegrityError)
        def handle_integrity_error(e: IntegrityError):
            db.session.rollback()

            if is_unique_violation(e):
                field = conflicting_field(e)
                message = (
                    f"{field} already exists" if field else "Record already exists"
                )
                return error_response(409, "Conflict", message)

            current_app.logger.warning("Constraint violation: %s", e.orig)
            return error_response(400, "Bad Request", "Data violates a constraint")

        @app.errorhandler(DataError)
        def handle_data_error(e: DataError):
            db.session.rollback()
            current_app.logger.warning("Invalid data for database: %s", e.orig)
            return error_response(400, "Bad Request", "Invalid value")

        @app.errorhandler(SQLAlchemyError)
        def handle_database_error(e: SQLAlchemyError):
            db.session.rollback()
            current_app.logger.exception("Database error")
            return error_response(500, "Internal Server Error", "Unexpected error")

        @app.errorhandler(HTTPException)
        def handle_http_exception(e: HTTPException):
            response = e.get_response()  # keeps headers like Allow, WWW-Authenticate
            response.data = jsonify(
                {"error": e.name, "message": e.description, "code": e.code}
            ).get_data()
            response.content_type = "application/json"
            return response

        @app.errorhandler(Exception)
        def handle_unexpected_error(e: Exception):
            current_app.logger.exception("Unhandled exception")
            return error_response(500, "Internal Server Error", "Unexpected error")
