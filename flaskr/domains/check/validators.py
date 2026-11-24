from marshmallow import fields, validate

from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
)
from flaskr.domains.check.models import CheckStatus


class CheckCreateValidator(BaseValidator):
    table_id = fields.Int(required=True, validate=validate.Range(min=1))
    product_id = fields.Int(required=True, validate=validate.Range(min=1))
    quantity = fields.Int(required=True, validate=validate.Range(min=1))


class CheckUpdateValidator(BaseValidator):
    product_id = fields.Int(required=True, validate=validate.Range(min=1))
    quantity = fields.Int(required=True, validate=validate.Range(min=0))  # 0 = remove


class CheckFilterValidator(BaseFilterValidator):
    table_id = fields.Int(validate=validate.Range(min=1))
    status = fields.Enum(CheckStatus, by_value=True)
    # ?start=2026-11-19&end=2026-11-20 -> CheckRepository.filter_start / filter_end
    start = fields.Date()
    end = fields.Date()


class CheckSortValidator(BaseSortValidator):
    SORT_FIELDS = {"created_at", "closed_at"}
