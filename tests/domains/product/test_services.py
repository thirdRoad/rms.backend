import pytest
from werkzeug.exceptions import Conflict, NotFound

from flaskr.domains.category.models import Category
from flaskr.domains.product.models import Product
from flaskr.domains.product.services import ProductService
from tests.base import BaseTestCase


class TestProductService(BaseTestCase):
    domain_class = ProductService
    domain: ProductService

    def seed_category(self, name: str = "Pizza") -> int:
        category = Category(name=name)
        self.db.session.add(category)
        self.db.session.commit()
        return category.id

    def seed_product(
        self,
        c_name: str = "Pizza",
        p_name: str = "Superix Pizza",
        price: float = 10.0,
        stock: int = 5,
    ) -> int:
        category_id = self.seed_category(name=c_name)
        product = Product(
            name=p_name,
            price=price,
            stock=stock,
            category_id=category_id,
        )
        self.db.session.add(product)
        self.db.session.commit()
        return product.id

    def test_create_new_product_returns_serialized_data(self):
        category_id = self.seed_category(name="Drinks")
        product_data = {
            "name": "Cola",
            "price": 5.0,
            "stock": 20,
            "category_id": category_id,
        }

        with self.app.test_request_context():
            result = self.domain.create_new_product(data=product_data)

            assert result["name"] == "Cola"
            assert result["price"] == 5.0
            assert result["stock"] == 20
            # assert result["category_id"] == category_id
            assert isinstance(result["id"], int)
            assert "created_at" in result

    def test_create_new_product_persists_to_db(self):
        category_id = self.seed_category(name="Drinks")
        product_data = {
            "name": "Cola",
            "price": 5.0,
            "stock": 20,
            "category_id": category_id,
        }

        with self.app.test_request_context():
            self.domain.create_new_product(data=product_data)

        saved = self.db.session.query(Product).filter_by(name="Cola").one_or_none()
        assert saved is not None
        assert saved.stock == 20
        assert saved.category_id == category_id

    def test_create_duplicate_product_raises_409(self):
        self.seed_product(c_name="Drinks", p_name="Cola", price=5.0, stock=20)
        category_id = self.seed_category(name="Beverages")

        duplicate_data = {
            "name": "Cola",
            "price": 6.0,
            "stock": 10,
            "category_id": category_id,
        }

        with self.app.test_request_context():
            with pytest.raises(Conflict) as exc_info:
                self.domain.create_new_product(data=duplicate_data)

            assert exc_info.value.code == 409
            assert "already exists" in exc_info.value.description
            assert "in category 'Drinks'" in exc_info.value.description

    def test_create_product_with_nonexistent_category_raises_404(self):
        product_data = {
            "name": "Tost",
            "price": 10.0,
            "stock": 0,
            "category_id": 999,
        }

        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.create_new_product(data=product_data)

            assert exc_info.value.description == "Category not found"

        saved = self.db.session.query(Product).filter_by(name="Tost").one_or_none()
        assert saved is None

    def test_get_by_id_returns_product(self):
        product_id = self.seed_product(
            c_name="Pizza", p_name="Superix Pizza", price=10.0, stock=5
        )

        with self.app.test_request_context():
            result = self.domain.get_by_id(item_id=product_id)

            assert result["id"] == product_id
            assert result["name"] == "Superix Pizza"
            assert result["price"] == 10.0
            assert result["stock"] == 5
            assert result["category"]["name"] == "Pizza"

    def test_get_by_id_returns_not_found_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.get_by_id(item_id=999)

            assert exc_info.value.code == 404

    def test_list_product_returns_all_products(self):
        self.seed_product(c_name="Pizza", p_name="Superix Pizza", price=10.0, stock=5)
        self.seed_product(
            c_name="Burger", p_name="Chicken Burger", price=11.0, stock=12
        )

        with self.app.test_request_context():
            result = self.domain.list_items()

            assert len(result) == 2
            assert {item["name"] for item in result} == {
                "Superix Pizza",
                "Chicken Burger",
            }
            assert {item["price"] for item in result} == {10.0, 11.0}
            assert {item["stock"] for item in result} == {5, 12}

    def test_list_items_empty_db_returns_empty_list(self):
        with self.app.test_request_context():
            assert self.domain.list_items() == []

    def test_update_item_changes_and_returns_data(self):
        product_id = self.seed_product(
            c_name="Pizza", p_name="Superix Pizza", price=10.0, stock=5
        )

        update_payload = {"name": "Mega Pizza", "price": 14.5, "stock": 10}

        with self.app.test_request_context():
            result = self.domain.update_item(item_id=product_id, data=update_payload)

            assert result["name"] == "Mega Pizza"
            assert result["price"] == 14.5
            assert result["stock"] == 10

    def test_update_nonexistent_item_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.update_item(
                    item_id=999, data={"name": "Nonexistent", "price": 10.0}
                )

    def test_delete_item_returns_true_and_removes(self):
        product_id = self.seed_product(
            c_name="Pizza", p_name="Superix Pizza", price=10.0, stock=5
        )

        with self.app.test_request_context():
            assert self.domain.delete_item(item_id=product_id) is True

            with pytest.raises(NotFound):
                self.domain.get_by_id(item_id=product_id)

    def test_delete_nonexistent_item_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.delete_item(item_id=999)
