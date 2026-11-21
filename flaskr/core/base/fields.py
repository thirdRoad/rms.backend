from typing import Any

from marshmallow import ValidationError, fields


class DelimitedList(fields.List):
    def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs) -> list:
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",") if item.strip()]
        if not value:
            raise ValidationError("At least one value is required.")
        return super()._deserialize(value, attr, data, **kwargs)
