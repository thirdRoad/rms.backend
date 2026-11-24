from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement


class Lookup(StrEnum):
    EQ = "eq"  # WHERE username = 'deniz'
    ICONTAINS = "icontains"  # WHERE lower(display_name) LIKE '%den%'
    GT = "gt"  # WHERE price > 50
    GTE = "gte"  # WHERE created_at >= '2026-11-01T00:00:00Z'
    LT = "lt"  # WHERE created_at < '2026-11-22T00:00:00Z'
    LTE = "lte"  # WHERE price <= 50
    IN = "in"  # WHERE status IN ('PREPARATION', 'DONE')  -- DelimitedList is required

    def apply(self, column: Any, value: Any) -> ColumnElement[bool]:
        match self:
            case Lookup.EQ:
                return column == value
            case Lookup.ICONTAINS:
                return column.icontains(value, autoescape=True)
            case Lookup.GT:
                return column > value
            case Lookup.GTE:
                return column >= value
            case Lookup.LT:
                return column < value
            case Lookup.LTE:
                return column <= value
            case Lookup.IN:
                return column.in_(value)
            case _:
                raise ValueError(f"No SQL condition defined for lookup '{self}'")
