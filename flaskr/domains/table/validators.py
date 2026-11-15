from typing import Any, Dict

from marshmallow import fields, validate

from flaskr.core.base.validators import BaseValidator
from flaskr.domains.table.models import TableStatus


class TableUpdateValidator(BaseValidator):
    status = fields.Str(
        required=True,
        validate=validate.OneOf([s.value for s in TableStatus]),
    )

    def get_table_status(self, data: Dict[str, Any]) -> TableStatus:
        data = self.validate_data(data=data)

        new_status = data["status"]
        return TableStatus[new_status.upper()]
