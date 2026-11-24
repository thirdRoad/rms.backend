from typing import Any, Dict, Generic, List, Type, TypeVar

from flask import abort

from flaskr.core.errors import not_found

T = TypeVar("T")


class BaseService(Generic[T]):
    repository: Type[T]
    domain: None | str = None  # e.g. "Order" -> "Order not found"

    def get_or_404(self, item_id: int) -> Any:
        item = self.repository.get_by_id(item_id=item_id)
        if item is None:
            not_found(self.domain)
        return item

    def get_by_id(self, item_id: int) -> Any | None:
        return self.get_or_404(item_id).serialize_detail

    def list_items(
        self, filters: None | Dict[str, Any] = None, sort: None | List[str] = None
    ) -> List:
        items = self.repository.get_all(filters=filters, sort=sort)
        return [item.serialize for item in items]

    def create_new_item(
        self,
        model_class,
        column_name: str,
        unique_key: str,
        func_name: str = "get_by_name",
        **kwargs,
    ) -> Dict | None:

        if existing_item := getattr(self.repository, func_name)(
            column_name, unique_key
        ):
            abort(
                code=409,
                description=f"{model_class.__name__} with {column_name}"
                f" '{unique_key}' already exists"
                f" (id: {existing_item.serialize.get("id")})",
            )

        new_item = self.repository.add(model_class(**kwargs))
        item_id = new_item.serialize.get("id")
        if item_id:
            return self.get_by_id(item_id=item_id)

    def update_item(self, item_id: int, data: Dict) -> Dict | None:
        self.get_by_id(item_id=item_id)
        response = self.repository.update(item_id=item_id, data=data)
        if response:
            return self.get_by_id(item_id=item_id)

    def delete_item(self, item_id: int) -> bool:
        self.get_by_id(item_id=item_id)
        return self.repository.delete(item_id=item_id)
