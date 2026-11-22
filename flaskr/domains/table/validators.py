from typing import Any

from marshmallow import ValidationError, fields, validates_schema

from flaskr.core.base.filters import Lookup
from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
    FieldOption,
)
from flaskr.domains.table.models import TableStatus


class TableValidator(BaseValidator):
    pass


class TableCreateValidator(TableValidator):
    status = fields.Enum(TableStatus, by_value=True)  # Optional, default -> available.


class TableUpdateValidator(
    TableValidator
):  # status is changed via /tables/<id>/<status>
    @validates_schema
    def require_any_field(self, data: dict[str, Any], **kwargs) -> None:
        if not data:
            raise ValidationError("At least one field must be provided.")


class TableFilterValidator(BaseFilterValidator):
    status = fields.Enum(TableStatus, by_value=True)
    created_from = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.GTE},
    )
    created_to = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.LT},
    )
    last_updated_from = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "last_updated", FieldOption.LOOKUP: Lookup.GTE},
    )
    last_updated_to = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "last_updated", FieldOption.LOOKUP: Lookup.LT},
    )


class TableSortValidator(BaseSortValidator):
    SORT_FIELDS = {"status", "created_at", "last_updated"}
