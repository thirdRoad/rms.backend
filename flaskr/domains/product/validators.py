from typing import Any

from marshmallow import ValidationError, fields, validate, validates_schema

from flaskr.core.base.filters import Lookup
from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
    FieldOption,
)


class ProductValidator(BaseValidator):
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50),
        metadata={FieldOption.STRIP: True},
    )
    price = fields.Float(required=True, validate=validate.Range(min=0))
    category_id = fields.Int(required=True, validate=validate.Range(min=1))


class ProductCreateValidator(ProductValidator):
    pass


class ProductUpdateValidator(ProductValidator):
    PARTIAL_FIELDS = {"name", "price", "category_id"}

    @validates_schema
    def require_any_field(self, data: dict[str, Any], **kwargs) -> None:
        if not data:
            raise ValidationError("At least one field must be provided.")


class ProductFilterValidator(BaseFilterValidator):
    name = fields.Str(
        validate=validate.Length(min=1, max=50),
        metadata={FieldOption.STRIP: True, FieldOption.LOOKUP: Lookup.ICONTAINS},
    )
    category = fields.Int(
        validate=validate.Range(min=1),
        metadata={FieldOption.COLUMN: "category_id"},
    )
    price_min = fields.Float(
        validate=validate.Range(min=0),
        metadata={FieldOption.COLUMN: "price", FieldOption.LOOKUP: Lookup.GTE},
    )
    price_max = fields.Float(
        validate=validate.Range(min=0),
        metadata={FieldOption.COLUMN: "price", FieldOption.LOOKUP: Lookup.LTE},
    )
    created_from = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.GTE},
    )
    created_to = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.LT},
    )


class ProductSortValidator(BaseSortValidator):
    SORT_FIELDS = {"name", "price", "created_at"}
