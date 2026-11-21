import pytest
from werkzeug.exceptions import Conflict, NotFound

from flaskr.domains.category.models import Category
from flaskr.domains.category.services import CategoryService
from tests.base import BaseTestCase


class TestCategoryService(BaseTestCase):
    domain_class = CategoryService
    domain: CategoryService

    def seed_category(self, name: str = "Drinks") -> int:
        category = Category(name=name)
        self.db.session.add(category)
        self.db.session.commit()
        return category.id

    def test_create_new_category_returns_serialized_data(self):
        with self.app.test_request_context():
            result = self.domain.create_new_category(data={"name": "Drinks"})

            assert result["name"] == "Drinks"
            assert isinstance(result["id"], int)
            assert "created_at" in result

    def test_create_new_category_persists_to_db(self):
        with self.app.test_request_context():
            self.domain.create_new_category(data={"name": "Drinks"})

        saved = self.db.session.query(Category).filter_by(name="Drinks").one_or_none()
        assert saved is not None

    def test_create_duplicate_category_raises_409(self):
        self.seed_category(name="Drinks")

        with self.app.test_request_context():
            with pytest.raises(Conflict) as exc_info:
                self.domain.create_new_category(data={"name": "Drinks"})

            assert exc_info.value.code == 409
            assert "already exists" in exc_info.value.description

    def test_get_by_id_returns_item(self):
        category_id = self.seed_category(name="Drinks")

        with self.app.test_request_context():
            result = self.domain.get_by_id(category_id)

            assert result["id"] == category_id
            assert result["name"] == "Drinks"

    def test_get_by_id_not_found_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.get_by_id(999)

            assert exc_info.value.code == 404

    def test_list_items_returns_all_serialized(self):
        self.seed_category(name="Drinks")
        self.seed_category(name="Desserts")

        with self.app.test_request_context():
            result = self.domain.list_items()

            assert len(result) == 2
            assert {item["name"] for item in result} == {"Drinks", "Desserts"}

    def test_list_items_empty_db_returns_empty_list(self):
        with self.app.test_request_context():
            assert self.domain.list_items() == []

    def test_update_item_changes_and_returns_data(self):
        category_id = self.seed_category(name="Drinks")

        with self.app.test_request_context():
            result = self.domain.update_item(
                item_id=category_id, data={"name": "Beverages"}
            )

            assert result["name"] == "Beverages"

    def test_update_nonexistent_item_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.update_item(item_id=999, data={"name": "Beverages"})

    def test_delete_item_returns_true_and_removes(self):
        category_id = self.seed_category(name="Drinks")

        with self.app.test_request_context():
            assert self.domain.delete_item(item_id=category_id) is True

            with pytest.raises(NotFound):
                self.domain.get_by_id(category_id)

    def test_delete_nonexistent_item_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.delete_item(item_id=999)
