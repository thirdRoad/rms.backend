from flaskr.core.extensions import db
from flaskr.core.security import hash_password
from flaskr.domains.category.models import Category
from flaskr.domains.category.services import CategoryService
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestCategoryAPI(BaseTestCase):
    domain_class = CategoryService
    domain: CategoryService

    def setup_case(self):
        admin_role = Role(name="admin")
        staff_role = Role(name="service_staff")
        kitchen_role = Role(name="kitchen_staff")
        db.session.add_all([admin_role, staff_role, kitchen_role])
        db.session.commit()

        users = [
            User(
                username="testadmin",
                password=hash_password("adminpass"),
                display_name="Admin",
                email="admin@test.com",
                role_id=admin_role.id,
            ),
            User(
                username="teststaff",
                password=hash_password("staffpass"),
                display_name="Staff",
                email="staff@test.com",
                role_id=staff_role.id,
            ),
            User(
                username="testkitchen",
                password=hash_password("kitchenpass"),
                display_name="Kitchen",
                email="kitchen@test.com",
                role_id=kitchen_role.id,
            ),
        ]
        db.session.add_all(users)
        db.session.commit()

    def get_auth_headers(
        self, username: str = "testadmin", password: str = "adminpass"
    ) -> dict:
        res = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        token = res.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_category(self, name: str = "Drinks") -> int:
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return category.id

    def test_create_category_returns_201(self):
        res = self.client.post(
            "/categories/",
            json={"name": "Drinks"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 201
        assert res.json["data"]["name"] == "Drinks"
        assert "id" in res.json["data"]
        assert "created_at" in res.json["data"]

    def test_create_duplicate_category_returns_409(self):
        self.create_category(name="Drinks")

        res = self.client.post(
            "/categories/",
            json={"name": "Drinks"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 409
        assert "already exists" in res.json["message"]

    def test_create_category_invalid_name_returns_400(self):
        res = self.client.post(
            "/categories/",
            json={"name": "ab"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["error"] == "Validation Error"
        assert "name" in res.json["message"]

    def test_create_category_missing_name_returns_400(self):
        res = self.client.post(
            "/categories/",
            json={},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert "name" in res.json["message"]

    def test_create_category_without_token_returns_401(self):
        res = self.client.post("/categories/", json={"name": "Drinks"})

        assert res.status_code == 401

    def test_create_category_as_service_staff_returns_403(self):

        res = self.client.post(
            "/categories/",
            json={"name": "Drinks"},
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403

    def test_list_categories_returns_count_and_data(self):
        self.create_category(name="Drinks")
        self.create_category(name="Desserts")

        res = self.client.get("/categories/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 2
        names = [item["name"] for item in res.json["data"]]
        assert "Drinks" in names
        assert "Desserts" in names

    def test_list_categories_as_service_staff_returns_200(self):

        res = self.client.get(
            "/categories/",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 200

    def test_list_categories_as_kitchen_staff_returns_403(self):
        res = self.client.get(
            "/categories/",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_get_category_by_id_returns_200(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.get(
            f"/categories/{category_id}/",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == category_id
        assert res.json["data"]["name"] == "Drinks"

    def test_get_nonexistent_category_returns_404(self):
        res = self.client.get("/categories/999/", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_update_category_returns_updated_data(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.patch(
            f"/categories/{category_id}/",
            json={"name": "Beverages"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["name"] == "Beverages"

        res = self.client.get(
            f"/categories/{category_id}/",
            headers=self.get_auth_headers(),
        )
        assert res.json["data"]["name"] == "Beverages"

    def test_update_nonexistent_category_returns_404(self):
        res = self.client.patch(
            "/categories/999/",
            json={"name": "Beverages"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404

    def test_update_category_as_service_staff_returns_403(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.patch(
            f"/categories/{category_id}/",
            json={"name": "Beverages"},
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403

    def test_delete_category_returns_204_and_removes_item(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.delete(
            f"/categories/{category_id}/",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 204

        res = self.client.get(
            f"/categories/{category_id}/",
            headers=self.get_auth_headers(),
        )
        assert res.status_code == 404

    def test_delete_nonexistent_category_returns_404(self):
        res = self.client.delete("/categories/999/", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_delete_category_as_service_staff_returns_403(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.delete(
            f"/categories/{category_id}/",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403
