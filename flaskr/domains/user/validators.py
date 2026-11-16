from typing import Any

from marshmallow import ValidationError, fields, validate, validates, validates_schema

from flaskr.core.base.validators import BaseValidator


class UserValidator(BaseValidator):
    HASH_FIELDS = {"password"}
    STRIP_FIELDS = {"display_name", "email"}
    LOWER_FIELDS = {"email"}

    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=32),
            validate.Regexp(
                r"^[a-z0-9_.]+\Z",
                error="Only lowercase letters, digits, '_' and '.' allowed.",
            ),
        ],
    )
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))
    display_name = fields.Str(required=True, validate=validate.Length(min=3, max=16))
    email = fields.Email(required=True, validate=validate.Length(max=64))
    role_id = fields.Int(required=True, validate=validate.Range(min=1))

    @validates("password")
    def password_not_blank(self, value: str, **kwargs) -> None:
        if not value.strip():
            raise ValidationError("Password cannot be blank.")


class UserCreateValidator(UserValidator):
    pass


class UserUpdateValidator(UserValidator):
    PARTIAL_FIELDS = {"username", "password", "display_name", "email", "role_id"}

    @validates_schema
    def require_any_field(self, data: dict[str, Any], **kwargs) -> None:
        if not data:
            raise ValidationError("At least one field must be provided.")
