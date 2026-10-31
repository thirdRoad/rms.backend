from werkzeug.security import generate_password_hash

from flaskr.core.extensions import db
from flaskr.domains.category.models import Category
from flaskr.domains.order.models import Order, OrderStatus
from flaskr.domains.order.services import OrderService
from flaskr.domains.order_item.models import OrderItem
from flaskr.domains.product.models import Product
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestOrderAPI(BaseTestCase):
    domain_class = OrderService
    domain: OrderService

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

    def seed_table(self) -> int:
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        return table.id

    def seed_product(
        self, name: str = "Pizza", price: float = 100.0, stock: int = 20
    ) -> int:
        category = Category(name=f"Cat for {name}")
        self.db.session.add(category)
        self.db.session.commit()

        product = Product(
            name=name,
            price=price,
            stock=stock,
            category_id=category.id,
        )
        self.db.session.add(product)
        self.db.session.commit()
        return product.id

    def create_order(self, user_username: str = "testadmin") -> dict:
        user = self.db.session.query(User).filter_by(username=user_username).first()
        table_id = self.seed_table()
        product1_id = self.seed_product(name="Pizza", price=200.0, stock=10)
        product2_id = self.seed_product(name="Cola", price=40.0, stock=50)

        order = Order(user_id=user.id, table_id=table_id)
        self.db.session.add(order)
        self.db.session.commit()

        od1 = OrderItem(
            order_id=order.id, product_id=product1_id, quantity=2, unit_price=200.0
        )
        od2 = OrderItem(
            order_id=order.id, product_id=product2_id, quantity=3, unit_price=40.0
        )
        self.db.session.add_all([od1, od2])
        self.db.session.commit()

        return {
            "order_id": order.id,
            "user_id": user.id,
            "table_id": table_id,
            "product1_id": product1_id,
            "product2_id": product2_id,
        }

    def test_create_order_returns_201(self):
        user = self.db.session.query(User).filter_by(username="testadmin").first()
        table_id = self.seed_table()
        product_id = self.seed_product(name="Burger", price=120.0, stock=15)

        payload = {
            "user_id": user.id,
            "table_id": table_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        }

        res = self.client.post(
            "/orders/",
            json=payload,
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 201
        assert "id" in res.json["data"]

    def test_create_order_with_nonexistent_product_returns_404(self):
        user = self.db.session.query(User).filter_by(username="testadmin").first()
        table_id = self.seed_table()

        payload = {
            "user_id": user.id,
            "table_id": table_id,
            "items": [{"product_id": 999, "quantity": 2}],
        }

        res = self.client.post(
            "/orders/",
            json=payload,
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Product not found: [999]"

    def test_create_order_invalid_payload_returns_400(self):
        res = self.client.post(
            "/orders/",
            json={"items": []},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400

    def test_create_order_without_token_returns_401(self):
        res = self.client.post("/orders/", json={})

        assert res.status_code == 401

    def test_create_order_as_service_staff_returns_201(self):
        user = self.db.session.query(User).filter_by(username="teststaff").first()
        table_id = self.seed_table()
        product_id = self.seed_product(name="Penne", price=150.0, stock=10)

        payload = {
            "user_id": user.id,
            "table_id": table_id,
            "items": [{"product_id": product_id, "quantity": 1}],
        }

        res = self.client.post(
            "/orders/",
            json=payload,
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 201

    def test_create_order_as_kitchen_staff_returns_403(self):
        user = self.db.session.query(User).filter_by(username="testkitchen").first()
        table_id = self.seed_table()
        product_id = self.seed_product(name="Toast", price=60.0, stock=10)

        payload = {
            "user_id": user.id,
            "table_id": table_id,
            "items": [{"product_id": product_id, "quantity": 1}],
        }

        res = self.client.post(
            "/orders/",
            json=payload,
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_get_order_by_id_returns_200(self):
        order_info = self.create_order(user_username="testadmin")
        order_id = order_info["order_id"]

        res = self.client.get(
            f"/orders/{order_id}",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == order_id
        assert res.json["data"]["user"]["username"] == "testadmin"
        assert res.json["data"]["user"]["created_at"].endswith("+00:00")

    def test_get_nonexistent_order_returns_404(self):
        res = self.client.get("/orders/999", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_get_order_by_id_as_kitchen_staff_returns_200(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.get(
            f"/orders/{order_id}",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 200

    def test_get_order_items_returns_200_and_items(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.get(
            f"/orders/{order_id}/items",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["count"] == 2
        product_ids = {item["product_id"] for item in res.json["data"]}
        assert product_ids == {order_info["product1_id"], order_info["product2_id"]}

    def test_get_order_items_nonexistent_order_returns_404(self):
        res = self.client.get(
            "/orders/999/items",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Order not found"

    def test_update_order_replaces_items_with_given_list(self):
        order_info = self.create_order()  # Pizza x2, Cola x3
        order_id = order_info["order_id"]
        burger_id = self.seed_product(name="Burger", price=150.0)

        res = self.client.patch(
            f"/orders/{order_id}",
            json={
                "items": [
                    {"product_id": order_info["product2_id"], "quantity": 10},
                    {"product_id": burger_id, "quantity": 1},
                ]
            },
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["count"] == 2
        quantities = {i["product_id"]: i["quantity"] for i in res.json["data"]}
        assert quantities == {order_info["product2_id"]: 10, burger_id: 1}

        removed = self.db.session.get(OrderItem, (order_id, order_info["product1_id"]))
        assert removed is None

        order = self.db.session.get(Order, order_id)
        assert order.table_id == order_info["table_id"]

    def test_update_order_as_service_staff_returns_200(self):
        order_info = self.create_order()

        res = self.client.patch(
            f"/orders/{order_info['order_id']}",
            json={"items": [{"product_id": order_info["product1_id"], "quantity": 4}]},
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 200

    def test_update_order_as_kitchen_staff_returns_403(self):
        order_info = self.create_order()

        res = self.client.patch(
            f"/orders/{order_info['order_id']}",
            json={"items": [{"product_id": order_info["product1_id"], "quantity": 4}]},
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_update_nonexistent_order_returns_404(self):
        res = self.client.patch(
            "/orders/999",
            json={"items": [{"product_id": 1, "quantity": 5}]},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Order not found"

    def test_update_order_with_nonexistent_product_returns_404(self):
        order_info = self.create_order()

        res = self.client.patch(
            f"/orders/{order_info['order_id']}",
            json={"items": [{"product_id": 999, "quantity": 1}]},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Product not found: [999]"

    def test_update_order_with_empty_items_returns_400(self):
        order_info = self.create_order()

        res = self.client.patch(
            f"/orders/{order_info['order_id']}",
            json={"items": []},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400

    def test_old_item_update_url_is_removed(self):
        order_info = self.create_order()

        res = self.client.patch(
            f"/orders/{order_info['order_id']}/items/{order_info['product1_id']}",
            json={"quantity": 5},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404

    def test_delete_order_items_returns_204_and_keeps_order(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}/items",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 204

        items_res = self.client.get(
            f"/orders/{order_id}/items",
            headers=self.get_auth_headers(),
        )
        assert items_res.status_code == 404
        assert items_res.json["message"] == "Order has no items"

        order_res = self.client.get(
            f"/orders/{order_id}",
            headers=self.get_auth_headers(),
        )
        assert order_res.status_code == 200

    def test_delete_order_items_as_service_staff_returns_204(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}/items",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 204

    def test_delete_order_items_as_kitchen_staff_returns_403(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}/items",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_delete_items_of_nonexistent_order_returns_404(self):
        res = self.client.delete(
            "/orders/999/items",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Order not found"

    def test_delete_order_returns_204_and_removes_order_with_items(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 204
        assert self.db.session.get(Order, order_id) is None
        assert (
            self.db.session.query(OrderItem).filter_by(order_id=order_id).count() == 0
        )

        get_res = self.client.get(
            f"/orders/{order_id}",
            headers=self.get_auth_headers(),
        )
        assert get_res.status_code == 404

    def test_delete_order_as_service_staff_returns_403(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}",
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 403
        assert self.db.session.get(Order, order_id) is not None

    def test_delete_order_as_kitchen_staff_returns_403(self):
        order_info = self.create_order()
        order_id = order_info["order_id"]

        res = self.client.delete(
            f"/orders/{order_id}",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_delete_nonexistent_order_returns_404(self):
        res = self.client.delete(
            "/orders/999",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Order not found"

    def post_status(self, order_id: int, status: str, user: str = "testadmin"):
        passwords = {
            "testadmin": "adminpass",
            "teststaff": "staffpass",
            "testkitchen": "kitchenpass",
        }
        return self.client.post(
            f"/orders/{order_id}/{status}",
            headers=self.get_auth_headers(user, passwords[user]),
        )

    def test_kitchen_staff_can_mark_order_done(self):
        order_id = self.create_order()["order_id"]

        res = self.post_status(order_id, "done", user="testkitchen")

        assert res.status_code == 200
        assert res.json["data"]["status"] == "done"
        assert self.db.session.get(Order, order_id).status == OrderStatus.DONE

    def test_service_staff_can_cancel_order(self):
        order_id = self.create_order()["order_id"]

        res = self.post_status(order_id, "cancelled", user="teststaff")

        assert res.status_code == 200
        assert res.json["data"]["status"] == "cancelled"

    def test_kitchen_staff_can_cancel_order(self):
        order_id = self.create_order()["order_id"]

        res = self.post_status(order_id, "cancelled", user="testkitchen")

        assert res.status_code == 200
        assert res.json["data"]["status"] == "cancelled"

    def test_status_can_move_between_any_statuses(self):
        order_id = self.create_order()["order_id"]

        for status in ("done", "cancelled", "done", "preparation", "cancelled"):
            res = self.post_status(order_id, status)

            assert res.status_code == 200
            assert res.json["data"]["status"] == status
            assert self.db.session.get(Order, order_id).status == OrderStatus(status)

    def test_setting_same_status_returns_409(self):
        order_id = self.create_order()["order_id"]

        res = self.post_status(order_id, "preparation")

        assert res.status_code == 409
        assert res.json["message"] == "Order is already preparation"

    def test_unknown_status_url_returns_404(self):
        order_id = self.create_order()["order_id"]

        res = self.post_status(order_id, "eaten")

        assert res.status_code == 404

    def test_old_status_patch_url_is_removed(self):
        order_id = self.create_order()["order_id"]

        res = self.client.patch(
            f"/orders/{order_id}/status",
            json={"status": "done"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404

    def test_status_of_nonexistent_order_returns_404(self):
        res = self.post_status(999, "done")

        assert res.status_code == 404
        assert res.json["message"] == "Order not found"
