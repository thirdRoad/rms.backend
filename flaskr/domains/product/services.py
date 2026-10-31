from typing import Any, Dict

from flask import abort

from flaskr.core.base.services import BaseService
from flaskr.domains.category.repositories import CategoryRepository
from flaskr.domains.product.models import Product
from flaskr.domains.product.repositories import ProductRepository


class ProductService(BaseService):
    repository: ProductRepository
    repository = ProductRepository()
    category_repo = CategoryRepository()

    def category_is_exists(self, category_id: int) -> bool:
        if self.category_repo.get_by_id(category_id) is None:
            abort(404, description="Category not found")
        return True

    def get_by_id(self, item_id: int) -> Any | None:
        product = self.repository.get_by_id(item_id)

        if product is None:
            abort(404, description="Product not found")

        response = product.serialize
        response["category"] = {
            "id": product.category.id,
            "name": product.category.name,
        }
        return response

    def create_new_product(self, data: Dict[str, Any]) -> Dict | None:
        self.category_is_exists(data["category_id"])

        return self.create_new_item(
            model_class=Product,
            unique_key=data["name"],
            column_name="name",
            **data,
        )

    def update_item(self, item_id: int, data: Dict) -> Dict | None:
        self.get_by_id(item_id=item_id)

        if "category_id" in data:
            self.category_is_exists(data["category_id"])

        return super().update_item(item_id=item_id, data=data)
