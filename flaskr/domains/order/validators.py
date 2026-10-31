from marshmallow import fields, validate

from flaskr.core.base.validators import BaseValidator


class OrderItemValidator(BaseValidator):
    product_id = fields.Integer(required=True, validate=validate.Range(min=1))
    quantity = fields.Integer(required=True, validate=validate.Range(min=1))


class OrderCreateValidator(BaseValidator):
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    table_id = fields.Integer(required=True, validate=validate.Range(min=1))

    items = fields.List(
        fields.Nested(OrderItemValidator),
        required=True,
        validate=validate.Length(
            min=1
        ),  # Conditions preventing sending an empty items list
    )


class OrderUpdateValidator(BaseValidator):
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
