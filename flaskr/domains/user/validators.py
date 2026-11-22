from typing import Any

from marshmallow import ValidationError, fields, validate, validates, validates_schema

from flaskr.core.base.filters import Lookup
from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
    FieldOption,
)


class UserValidator(BaseValidator):
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
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=128),
        metadata={FieldOption.HASH: True},
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=16),
        metadata={FieldOption.STRIP: True},
    )
    email = fields.Email(
        required=True,
        validate=validate.Length(max=64),
        metadata={FieldOption.STRIP: True, FieldOption.LOWER: True},
    )
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


class UserFilterValidator(BaseFilterValidator):
    username = fields.Str(
        validate=validate.Length(min=1, max=32),
        metadata={FieldOption.STRIP: True, FieldOption.LOWER: True},
    )
    display_name = fields.Str(
        validate=validate.Length(min=1, max=16),
        metadata={FieldOption.STRIP: True, FieldOption.LOOKUP: Lookup.ICONTAINS},
    )
    email = fields.Str(
        validate=validate.Length(min=1, max=64),
        metadata={FieldOption.STRIP: True, FieldOption.LOWER: True},
    )
    role = fields.Int(
        validate=validate.Range(min=1),
        metadata={FieldOption.COLUMN: "role_id"},
    )
    # ?created_from=2026-11-01T00:00:00Z&created_to=2026-11-22T00:00:00Z (UTC)
    created_from = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.GTE},
    )
    created_to = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.LT},
    )
    # IN example (not used yet) - several roles at once, ?roles=1,2:
    # roles = DelimitedList(
    #     fields.Int(validate=validate.Range(min=1)),
    #     metadata={FieldOption.COLUMN: "role_id", FieldOption.LOOKUP: Lookup.IN},
    # )


class UserSortValidator(BaseSortValidator):
    SORT_FIELDS = {"username", "display_name", "email", "created_at"}
