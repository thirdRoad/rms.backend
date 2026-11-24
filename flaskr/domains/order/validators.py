from marshmallow import fields, validate

from flaskr.core.base.filters import Lookup
from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
    FieldOption,
)
from flaskr.domains.order.models import OrderStatus


class OrderItemValidator(BaseValidator):
    product_id = fields.Integer(required=True, validate=validate.Range(min=1))
    quantity = fields.Integer(required=True, validate=validate.Range(min=1))


class OrderValidator(BaseValidator):
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    table_id = fields.Int(required=True, validate=validate.Range(min=1))
    items = fields.List(
        fields.Nested(OrderItemValidator),
        required=True,
        validate=validate.Length(min=1),  # prevents an empty items list
    )


class OrderCreateValidator(OrderValidator):
    pass


class OrderUpdateValidator(BaseValidator):
    items = fields.List(
        fields.Nested(OrderItemValidator),
        required=True,
        validate=validate.Length(min=1),
    )


class OrderFilterValidator(BaseFilterValidator):
    status = fields.Enum(OrderStatus, by_value=True)  # ?status=preparation
    user = fields.Int(
        validate=validate.Range(min=1),
        metadata={FieldOption.COLUMN: "user_id"},
    )
    table = fields.Int(
        validate=validate.Range(min=1),
        metadata={FieldOption.COLUMN: "table_id"},
    )
    # ?created_from=2026-11-01T00:00:00Z&created_to=2026-11-22T00:00:00Z (UTC)
    created_from = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.GTE},
    )
    created_to = fields.AwareDateTime(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.LT},
    )


class OrderSortValidator(BaseSortValidator):
    SORT_FIELDS = {"status", "created_at", "user_id", "table_id"}
