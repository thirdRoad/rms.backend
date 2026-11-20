from typing import List

from sqlalchemy import select

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.domains.category.models import Category
from flaskr.domains.product.models import Product


class ProductRepository(BaseRepository[Product]):
    model = Product

    def search_by_product_name(self, value: str) -> List[Product]:
        query = select(self.model).where(self.model.name.contains(value))
        return db.session.scalars(query).all()

    def filter_by_category(self, category_id: int) -> List[Product]:
        query = (
            select(self.model)
            .join(self.model.category)
            .where(Category.id == category_id)
        )
        return db.session.scalars(query).all()
