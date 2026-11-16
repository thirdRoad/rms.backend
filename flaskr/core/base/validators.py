from typing import Any

from marshmallow import Schema, post_load, pre_load
from werkzeug.security import generate_password_hash


class BaseValidator(Schema):
    HASH_FIELDS: set[str] = set()
    STRIP_FIELDS: set[str] = set()  # only trim
    LOWER_FIELDS: set[str] = set()  # only lowercase
    PARTIAL_FIELDS: set[str] = set()  # Optional fields.

    @pre_load
    def normalize_fields(self, data: Any, **kwargs) -> Any:
        if not isinstance(data, dict):
            return data
        for field in self.STRIP_FIELDS | self.LOWER_FIELDS:
            if isinstance(value := data.get(field), str):
                if field in self.STRIP_FIELDS:
                    value = value.strip()
                if field in self.LOWER_FIELDS:
                    value = value.lower()
                data[field] = value
        return data

    @post_load
    def hash_fields(self, data: dict[str, Any], **kwargs) -> dict[str, Any]:
        for field in self.HASH_FIELDS:
            if value := data.get(field):
                data[field] = generate_password_hash(value)
        return data

    def validate_data(self, data: dict[str, Any] | None) -> dict[str, Any]:
        return self.load(data, partial=self.PARTIAL_FIELDS)
