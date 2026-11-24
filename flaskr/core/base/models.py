from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column


def mapped_foreign_key(target, **kwargs):
    return mapped_column(ForeignKey(target), **kwargs)


class BaseModel(DeclarativeBase):
    @property
    def serialize(self) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must define serialize")

    @property
    def serialize_detail(self) -> dict[str, Any]:
        # single-item representation; override to add related data
        return self.serialize
