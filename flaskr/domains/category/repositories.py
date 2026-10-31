from flaskr.core.base.repositories import BaseRepository
from flaskr.domains.category.models import Category


class CategoryRepository(BaseRepository[Category]):
    model = Category
