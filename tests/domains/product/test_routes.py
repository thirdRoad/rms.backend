from werkzeug.security import generate_password_hash

from flaskr.core.extensions import db
from flaskr.domains.category.models import Category
from flaskr.domains.product.models import Product
from flaskr.domains.product.services import ProductService
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestProductAPI(BaseTestCase):
    domain_class = ProductService
    domain: ProductService

    def setup_case(self):

        admin_role = Role(name="admin")
        staff_role = Role(name="service_staff")
        kitchen_role = Role(name="kitchen_staff")
        db.session.add_all([admin_role, staff_role, kitchen_role])
        db.session.commit()

        users = [
            User(
                username="testadmin",
                password=generate_password_hash("adminpass"),
                display_name="Admin",
                email="admin@test.com",
                role_id=admin_role.id,
            ),
            User(
                username="teststaff",
                password=generate_password_hash("staffpass"),
                display_name="Staff",
                email="staff@test.com",
                role_id=staff_role.id,
            ),
            User(
                username="testkitchen",
                password=generate_password_hash("kitchenpass"),
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

    def create_category(self, name: str = "Fast Food") -> int:
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return category.id

    def create_product(
        self,
        name: str = "Cheeseburger",
        price: float = 12.5,
        stock: int = 25,
        category_id: int | None = None,
    ) -> int:
        if category_id is None:
            category_id = self.create_category(name=f"Category for {name}")

        product = Product(
            name=name,
            price=price,
            stock=stock,
            category_id=category_id,
        )
        db.session.add(product)
        db.session.commit()
        return product.id

    def test_create_product_returns_201(self):
        category_id = self.create_category(name="Burgers")
        payload = {
            "name": "Cheeseburger",
            "price": 12.5,
            "stock": 20,
            "category_id": category_id,
        }

        res = self.client.post(
            "/products/",
            json=payload,
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 201
        assert res.json["data"]["name"] == "Cheeseburger"
        assert res.json["data"]["price"] == 12.5
        assert res.json["data"]["stock"] == 20
        assert "id" in res.json["data"]
        assert "created_at" in res.json["data"]

    def test_create_duplicate_product_returns_409(self):
        category_id = self.create_category(name="Burgers")
        self.create_product(name="Cheeseburger", category_id=category_id)

        res = self.client.post(
            "/products/",
            json={
                "name": "Cheeseburger",
                "price": 15.0,
                "stock": 10,
                "category_id": category_id,
            },
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 409
        assert "already exists" in res.json["message"]
        assert "in category 'Burgers'" in res.json["message"]

    def test_create_product_with_nonexistent_category_returns_404(self):
        res = self.client.post(
            "/products/",
            json={
                "name": "Tost",
                "price": 10.0,
                "stock": 0,
                "category_id": 999,
            },
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Category not found"

    def test_create_product_missing_required_fields_returns_400(self):
        res = self.client.post(
            "/products/",
            json={"name": "Incomplete Product"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert "Validation Error" in res.json.get("error", "Validation Error")

    def test_create_product_without_token_returns_401(self):
        res = self.client.post(
            "/products/",
            json={"name": "Unauthorized Product", "price": 10.0, "stock": 5},
        )

        assert res.status_code == 401

    def test_create_product_as_service_staff_returns_403(self):
        category_id = self.create_category(name="Drinks")

        res = self.client.post(
            "/products/",
            json={
                "name": "Cola",
                "price": 5.0,
                "stock": 50,
                "category_id": category_id,
            },
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403

    def test_list_products_returns_count_and_data(self):
        category_id = self.create_category(name="Meals")
        self.create_product(name="Pizza", price=20.0, stock=10, category_id=category_id)
        self.create_product(name="Pasta", price=15.0, stock=15, category_id=category_id)

        res = self.client.get("/products/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 2
        names = [item["name"] for item in res.json["data"]]
        assert "Pizza" in names
        assert "Pasta" in names

    def test_list_products_as_service_staff_returns_200(self):
        res = self.client.get(
            "/products/",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 200

    def test_list_products_as_kitchen_staff_returns_403(self):
        res = self.client.get(
            "/products/",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_list_products_without_token_returns_401(self):
        res = self.client.get("/products/")

        assert res.status_code == 401

    def test_get_product_by_id_returns_200_and_category_details(self):
        category_id = self.create_category(name="Desserts")
        product_id = self.create_product(
            name="Tiramisu", price=8.5, stock=12, category_id=category_id
        )

        res = self.client.get(
            f"/products/{product_id}",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == product_id
        assert res.json["data"]["name"] == "Tiramisu"
        assert res.json["data"]["price"] == 8.5
        assert res.json["data"]["stock"] == 12
        assert res.json["data"]["category"]["id"] == category_id
        assert res.json["data"]["category"]["name"] == "Desserts"

    def test_get_product_by_id_as_service_staff_returns_200(self):
        product_id = self.create_product(name="Lemonade")

        res = self.client.get(
            f"/products/{product_id}",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 200

    def test_get_product_by_id_as_kitchen_staff_returns_403(self):
        product_id = self.create_product(name="Lemonade")

        res = self.client.get(
            f"/products/{product_id}",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_get_nonexistent_product_returns_404(self):
        res = self.client.get("/products/999", headers=self.get_auth_headers())

        assert res.status_code == 404
        assert res.json["message"] == "Product not found"

    def test_update_product_returns_updated_data(self):
        product_id = self.create_product(name="Pizzaaa", price=10.0, stock=5)

        res = self.client.patch(
            f"/products/{product_id}",
            json={"name": "Pizza", "price": 14.0, "stock": 8},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["name"] == "Pizza"
        assert res.json["data"]["price"] == 14.0
        assert res.json["data"]["stock"] == 8

        get_res = self.client.get(
            f"/products/{product_id}",
            headers=self.get_auth_headers(),
        )
        assert get_res.json["data"]["name"] == "Pizza"

    def test_update_nonexistent_product_returns_404(self):
        res = self.client.patch(
            "/products/999",
            json={"name": "Pizza", "price": 10.0},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404

    def test_update_product_with_nonexistent_category_returns_404(self):
        product_id = self.create_product(name="Pizza", price=10.0, stock=5)

        res = self.client.patch(
            f"/products/{product_id}",
            json={"category_id": 999},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Category not found"

    def test_update_product_as_kitchen_staff_returns_403(self):
        product_id = self.create_product(name="Ice Cream")

        res = self.client.patch(
            f"/products/{product_id}",
            json={"price": 15.0},
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_delete_product_returns_204_and_removes_item(self):
        product_id = self.create_product(name="to be deleted")

        res = self.client.delete(
            f"/products/{product_id}",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 204

        get_res = self.client.get(
            f"/products/{product_id}",
            headers=self.get_auth_headers(),
        )
        assert get_res.status_code == 404

    def test_delete_nonexistent_product_returns_404(self):
        res = self.client.delete("/products/999", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_delete_product_as_service_staff_returns_403(self):
        product_id = self.create_product(name="Burger")

        res = self.client.delete(
            f"/products/{product_id}",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403
