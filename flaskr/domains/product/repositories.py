from flaskr.core.base.repositories import BaseRepository
from flaskr.domains.product.models import Product


class ProductRepository(BaseRepository[Product]):
    model = Product
