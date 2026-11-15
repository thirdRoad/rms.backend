from flask import jsonify
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from flaskr.core.extensions import db

PG_UNIQUE_VIOLATION = "23505"


def is_unique_violation(e: IntegrityError) -> bool:
    if getattr(e.orig, "pgcode", None) == PG_UNIQUE_VIOLATION:
        return True
    return "UNIQUE constraint failed" in str(e.orig)  # SQLite (tests)


def integrity_error_detail(e: IntegrityError) -> None | str:
    diag = getattr(e.orig, "diag", None)  # e.g. "Key (name)=(Cola) already exists."
    return getattr(diag, "message_detail", None)


class ErrorHandler:
    @staticmethod
    def init_app(app):
        @app.errorhandler(Exception)
        def handle_exception(e):
            if isinstance(e, IntegrityError):
                db.session.rollback()
                detail = integrity_error_detail(e)

                if is_unique_violation(e):
                    message = detail or "A record with the same unique value exists"
                    code, error = 409, "Conflict"
                else:
                    message = detail or "Data violates a database constraint"
                    code, error = 400, "Bad Request"

                return jsonify({"error": error, "message": message, "code": code}), code

            if isinstance(e, ValidationError):
                return (
                    jsonify(
                        {
                            "error": "Validation Error",
                            "message": e.messages,
                            "code": 400,
                        }
                    ),
                    400,
                )

            if isinstance(e, HTTPException):
                response = {"error": e.name, "message": e.description, "code": e.code}
                return jsonify(response), e.code

            response = {
                "error": "Internal Server Error",
                "message": f"Flask error: {e}",
                "code": 500,
            }
            return jsonify(response), 500
