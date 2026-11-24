from enum import StrEnum
from typing import Any

from marshmallow import (
    EXCLUDE,
    Schema,
    ValidationError,
    fields,
    post_load,
    pre_load,
    validates,
)
from werkzeug.datastructures import MultiDict

from flaskr.core.base.filters import Lookup
from flaskr.core.security import hash_password


class FieldOption(StrEnum):
    STRIP = "strip"  # trim surrounding whitespace (before validation)
    LOWER = "lower"  # lowercase (before validation)
    HASH = "hash"  # replace value with its password hash (after validation)
    COLUMN = "column"  # target model column (BaseFilterValidator)
    LOOKUP = "lookup"  # Lookup operator (BaseFilterValidator)


class BaseValidator(Schema):
    PARTIAL_FIELDS: set[str] = set()  # Optional fields.

    @pre_load
    def normalize_fields(self, data: Any, **kwargs) -> Any:
        if not isinstance(data, dict):
            return data
        for name, field in self.load_fields.items():
            if not isinstance(value := data.get(name), str):
                continue
            if field.metadata.get(FieldOption.STRIP):
                value = value.strip()
            if field.metadata.get(FieldOption.LOWER):
                value = value.lower()
            data[name] = value
        return data

    @post_load
    def hash_fields(self, data: dict[str, Any], **kwargs) -> dict[str, Any]:
        for name, field in self.load_fields.items():
            if field.metadata.get(FieldOption.HASH) and (value := data.get(name)):
                data[name] = hash_password(value)
        return data

    def validate_data(self, data: dict[str, Any] | None) -> dict[str, Any]:
        return self.load(data, partial=self.PARTIAL_FIELDS)


class BaseQueryValidator(BaseValidator):
    class Meta:
        unknown = EXCLUDE  # ignore unrelated params

    def validate_query(self, args: MultiDict[str, str]) -> dict[str, Any]:
        params = {key: value for key, value in args.to_dict().items() if value.strip()}
        validated_params = self.validate_data(params)
        return self.transform(validated_params)

    def transform(self, validated_params: dict[str, Any]) -> dict[str, Any]:
        return validated_params


class BaseFilterValidator(BaseQueryValidator):
    def transform(self, validated_params: dict[str, Any]) -> dict[str, Any]:
        return {
            f"{self.column_for(key)}__{self.lookup_for(key)}": value
            for key, value in validated_params.items()
        }

    def column_for(self, field_name: str) -> str:
        return self.fields[field_name].metadata.get(FieldOption.COLUMN, field_name)

    def lookup_for(self, field_name: str) -> Lookup:
        return self.fields[field_name].metadata.get(FieldOption.LOOKUP, Lookup.EQ)


class BaseSortValidator(BaseQueryValidator):
    SORT_FIELDS: set[str] = set()  # allowed columns
    sort = fields.Str()

    @validates("sort")
    def validate_sort(self, value: str, **kwargs) -> None:
        invalid = [
            item
            for item in self.split(value)
            if item.lstrip("-") not in self.SORT_FIELDS
        ]
        if invalid:
            raise ValidationError(
                f"Invalid sort field(s): {', '.join(invalid)}. "
                f"Allowed: {', '.join(sorted(self.SORT_FIELDS))}."
            )

    def transform(self, validated_params: dict[str, Any]) -> dict[str, Any]:
        return {"sort": self.split(validated_params.get("sort", ""))}

    @staticmethod
    def split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]
