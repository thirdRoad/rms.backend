from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import ColumnElement, Select, UnaryExpression, select
from sqlalchemy.exc import SQLAlchemyError

from flaskr.core.base.filters import Lookup
from flaskr.core.extensions import db

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: Type[T]

    def build_conditions(
        self, filters: None | Dict[str, Any] = None
    ) -> List[ColumnElement[bool]]:
        # {"status__eq": "done"} -> [Order.status == "done"]
        conditions = []
        for key, value in (filters or {}).items():
            name, lookup = key.split("__")
            # Hook for conditions that are not "column <op> value", e.g.
            # def filter_in_stock(self, value): return Product.stock > 0
            if custom_filter := getattr(self, f"filter_{name}", None):
                conditions.append(custom_filter(value))
                continue
            column = getattr(self.model, name)
            conditions.append(Lookup(lookup).apply(column, value))
        return conditions

    def build_ordering(self, sort: None | List[str] = None) -> List[UnaryExpression]:
        # ["-created_at", "name"] -> [created_at DESC, name ASC, id ASC]
        ordering = []
        for item in sort or []:
            column = getattr(self.model, item.lstrip("-"))
            ordering.append(column.desc() if item.startswith("-") else column.asc())
        ordering.append(self.model.id.asc())  # stable order for equal values
        return ordering

    def build_query(
        self, filters: None | Dict[str, Any] = None, sort: None | List[str] = None
    ) -> Select:
        return (
            select(self.model)
            .where(*self.build_conditions(filters))
            .order_by(*self.build_ordering(sort))
        )

    def get_all(
        self, filters: None | Dict[str, Any] = None, sort: None | List[str] = None
    ) -> List[T]:
        return list(db.session.scalars(self.build_query(filters, sort)).all())

    def get_by_id(self, item_id: int) -> Optional[T]:
        return db.session.get(self.model, item_id)

    def get_by_name(self, column_name: str, value: Any) -> Optional[T]:
        filter_criteria = {column_name: value}
        query = select(self.model).filter_by(**filter_criteria)
        return db.session.execute(query).scalars().one_or_none()

    def update(self, item_id: int, data: Dict) -> bool:
        entity = db.session.get(self.model, item_id)

        for key, value in data.items():
            if hasattr(entity, key) and key != "id":
                setattr(entity, key, value)

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        return True

    def add(self, entity: T) -> T:
        db.session.add(entity)
        db.session.commit()
        return entity

    def delete(self, item_id: int) -> bool:
        entity = self.get_by_id(item_id=item_id)
        db.session.delete(entity)
        db.session.commit()

        return True
