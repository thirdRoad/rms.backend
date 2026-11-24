from datetime import datetime, timezone

from flaskr.core.extensions import db
from flaskr.core.security import hash_password
from flaskr.domains.category.models import Category
from flaskr.domains.check.models import (
    Check,
    CheckProduct,
    CheckProductSource,
    CheckStatus,
)
from flaskr.domains.check.services import CheckService
from flaskr.domains.order.models import Order, OrderStatus
from flaskr.domains.order_item.models import OrderItem
from flaskr.domains.product.models import Product
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestCheckAPI(BaseTestCase):
    domain_class = CheckService
    domain: CheckService

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
        self.user_id = users[0].id

        self.table_id = self.seed_table()
        self.water_id = self.seed_product(name="Su", price=30.0)
        self.kofte_id = self.seed_product(name="Köfte", price=180.0)
        self.ayran_id = self.seed_product(name="Ayran", price=65.0)

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
        db.session.add(table)
        db.session.commit()
        return table.id

    def seed_product(self, name: str, price: float) -> int:
        category = Category(name=f"Cat for {name}")
        db.session.add(category)
        db.session.commit()

        product = Product(name=name, price=price, stock=10, category_id=category.id)
        db.session.add(product)
        db.session.commit()
        return product.id

    def seed_order(
        self,
        items: list[tuple[int, int, float]],
        table_id: int | None = None,
        status: OrderStatus = OrderStatus.PREPARATION,
    ) -> int:
        order = Order(
            user_id=self.user_id, table_id=table_id or self.table_id, status=status
        )
        db.session.add(order)
        db.session.commit()

        db.session.add_all(
            OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
            )
            for product_id, quantity, unit_price in items
        )
        db.session.commit()
        return order.id

    def add_product(
        self, product_id: int, quantity: int = 1, table_id: int | None = None
    ):
        return self.client.post(
            "/checks/",
            json={
                "table_id": table_id or self.table_id,
                "product_id": product_id,
                "quantity": quantity,
            },
            headers=self.get_auth_headers(),
        )

    def open_check(self) -> int:
        return self.add_product(self.water_id, quantity=2).json["data"]["id"]

    def seed_closed_check(
        self, status: CheckStatus, closed_at: datetime, total: float
    ) -> int:
        check = Check(
            table_id=self.table_id,
            status=status,
            created_at=closed_at,
            closed_at=closed_at,
            total=total,
        )
        db.session.add(check)
        db.session.commit()
        return check.id

    # POST /checks

    def test_add_product_opens_check_returns_201(self):
        res = self.add_product(self.water_id, quantity=2)

        assert res.status_code == 201
        data = res.json["data"]
        assert list(data) == [
            "id",
            "table_id",
            "status",
            "created_at",
            "closed_at",
            "total",
            "products",
        ]
        assert data["table_id"] == self.table_id
        assert data["status"] == "open"
        assert data["created_at"].endswith("+00:00")
        assert data["closed_at"] is None
        assert data["total"] == 60.0
        assert data["products"] == [
            {
                "product_id": self.water_id,
                "product_name": "Su",
                "quantity": 2,
                "unit_price": 30.0,
                "source": "check",
                "order_id": None,
            }
        ]
        assert db.session.get(Table, self.table_id).status == TableStatus.OCCUPIED

    def test_add_product_to_open_check_returns_200_and_same_check(self):
        check_id = self.open_check()

        res = self.add_product(self.ayran_id)

        assert res.status_code == 200
        assert res.json["data"]["id"] == check_id
        assert len(res.json["data"]["products"]) == 2
        assert res.json["data"]["total"] == 125.0
        assert db.session.query(Check).count() == 1

    def test_add_same_product_increments_quantity(self):
        self.open_check()

        res = self.add_product(self.water_id, quantity=3)

        products = res.json["data"]["products"]
        assert len(products) == 1
        assert products[0]["quantity"] == 5
        assert res.json["data"]["total"] == 150.0

    def test_add_product_as_service_staff_returns_201(self):
        res = self.client.post(
            "/checks/",
            json={
                "table_id": self.table_id,
                "product_id": self.water_id,
                "quantity": 1,
            },
            headers=self.get_auth_headers("teststaff", "staffpass"),
        )

        assert res.status_code == 201

    def test_add_product_as_kitchen_staff_returns_403(self):
        res = self.client.post(
            "/checks/",
            json={
                "table_id": self.table_id,
                "product_id": self.water_id,
                "quantity": 1,
            },
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_add_product_without_token_returns_401(self):
        res = self.client.post("/checks/", json={})

        assert res.status_code == 401

    def test_add_product_with_zero_quantity_returns_400(self):
        res = self.add_product(self.water_id, quantity=0)

        assert res.status_code == 400
        assert res.json["error"] == "Validation Error"
        assert res.json["message"] == {
            "quantity": ["Must be greater than or equal to 1."]
        }

    def test_add_product_without_quantity_returns_400(self):
        res = self.client.post(
            "/checks/",
            json={"table_id": self.table_id, "product_id": self.water_id},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert "quantity" in res.json["message"]

    def test_add_product_nonexistent_table_returns_404(self):
        res = self.add_product(self.water_id, table_id=999)

        assert res.status_code == 404
        assert res.json["message"] == "Table not found"

    def test_add_nonexistent_product_returns_404(self):
        res = self.add_product(999)

        assert res.status_code == 404
        assert res.json == {
            "error": "Not Found",
            "message": "Product not found",
            "code": 404,
        }
        assert db.session.query(Check).count() == 0

    def test_add_product_after_close_opens_new_check(self):
        first_id = self.open_check()
        self.client.post(f"/checks/{first_id}/close", headers=self.get_auth_headers())

        res = self.add_product(self.water_id)

        assert res.status_code == 201
        assert res.json["data"]["id"] != first_id

    # GET /checks/<id>

    def test_get_open_check_includes_live_order_products(self):
        check_id = self.open_check()
        order_id = self.seed_order(
            [(self.kofte_id, 2, 180.0), (self.ayran_id, 1, 65.0)]
        )

        res = self.client.get(f"/checks/{check_id}", headers=self.get_auth_headers())

        assert res.status_code == 200
        data = res.json["data"]
        assert data["total"] == 485.0
        assert data["products"][1:] == [
            {
                "product_id": self.kofte_id,
                "product_name": "Köfte",
                "quantity": 2,
                "unit_price": 180.0,
                "source": "order",
                "order_id": order_id,
            },
            {
                "product_id": self.ayran_id,
                "product_name": "Ayran",
                "quantity": 1,
                "unit_price": 65.0,
                "source": "order",
                "order_id": order_id,
            },
        ]

    def test_get_open_check_skips_cancelled_and_other_table_orders(self):
        check_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)], status=OrderStatus.CANCELLED)
        self.seed_order([(self.ayran_id, 1, 65.0)], table_id=self.seed_table())

        res = self.client.get(f"/checks/{check_id}", headers=self.get_auth_headers())

        assert [p["source"] for p in res.json["data"]["products"]] == ["check"]
        assert res.json["data"]["total"] == 60.0

    def test_get_check_as_kitchen_staff_returns_200(self):
        check_id = self.open_check()

        res = self.client.get(
            f"/checks/{check_id}",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 200

    def test_get_nonexistent_check_returns_404(self):
        res = self.client.get("/checks/999", headers=self.get_auth_headers())

        assert res.status_code == 404
        assert res.json["message"] == "Check not found"

    # GET /checks

    def test_list_checks_returns_totals_without_products(self):
        check_id = self.open_check()
        self.seed_order([(self.kofte_id, 1, 180.0)])
        paid_id = self.seed_closed_check(
            CheckStatus.PAID,
            datetime(2026, 11, 19, 21, 45, tzinfo=timezone.utc),
            1240.0,
        )

        res = self.client.get("/checks/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 2
        totals = {c["id"]: c["total"] for c in res.json["data"]}
        assert totals == {check_id: 240.0, paid_id: 1240.0}
        assert all("products" not in c for c in res.json["data"])

    def test_list_checks_filters_by_status_and_table(self):
        self.open_check()
        paid_id = self.seed_closed_check(
            CheckStatus.PAID, datetime(2026, 11, 19, 21, 45, tzinfo=timezone.utc), 10.0
        )
        other_table_id = self.seed_table()
        self.add_product(self.water_id, table_id=other_table_id)

        res = self.client.get(
            f"/checks/?status=paid&table_id={self.table_id}",
            headers=self.get_auth_headers(),
        )

        assert [c["id"] for c in res.json["data"]] == [paid_id]

    def test_list_checks_filters_by_closed_at_for_closed_checks(self):
        in_range = self.seed_closed_check(
            CheckStatus.PAID, datetime(2026, 11, 20, 23, 59, tzinfo=timezone.utc), 1.0
        )
        self.seed_closed_check(
            CheckStatus.PAID, datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc), 1.0
        )
        self.seed_closed_check(
            CheckStatus.CANCELLED, datetime(2026, 11, 21, 0, 0, tzinfo=timezone.utc), 0
        )

        res = self.client.get(
            "/checks/?start=2026-11-19&end=2026-11-20", headers=self.get_auth_headers()
        )

        assert res.status_code == 200
        assert [c["id"] for c in res.json["data"]] == [in_range]

    def test_list_checks_filters_open_check_by_created_at(self):
        check_id = self.open_check()
        today = datetime.now(timezone.utc).date().isoformat()

        res = self.client.get(
            f"/checks/?start={today}&end={today}", headers=self.get_auth_headers()
        )
        assert [c["id"] for c in res.json["data"]] == [check_id]

        res = self.client.get(
            "/checks/?end=2000-01-01", headers=self.get_auth_headers()
        )
        assert res.json["count"] == 0

    def test_list_checks_invalid_date_returns_400(self):
        res = self.client.get(
            "/checks/?start=yesterday", headers=self.get_auth_headers()
        )

        assert res.status_code == 400
        assert res.json["message"] == {"start": ["Not a valid date."]}

    def test_list_checks_invalid_status_returns_400(self):
        res = self.client.get("/checks/?status=closed", headers=self.get_auth_headers())

        assert res.status_code == 400
        assert "status" in res.json["message"]

    # PATCH /checks/<id>

    def test_update_product_quantity_returns_detail(self):
        check_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)])

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.water_id, "quantity": 3},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["products"][0]["quantity"] == 3
        assert res.json["data"]["total"] == 450.0

    def test_update_product_quantity_zero_removes_it(self):
        check_id = self.open_check()

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.water_id, "quantity": 0},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["products"] == []
        assert res.json["data"]["total"] == 0
        assert db.session.query(CheckProduct).count() == 0

    def test_update_product_negative_quantity_returns_400(self):
        check_id = self.open_check()

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.water_id, "quantity": -1},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["message"] == {
            "quantity": ["Must be greater than or equal to 0."]
        }

    def test_update_order_product_returns_409(self):
        check_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)])

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.kofte_id, "quantity": 1},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 409
        assert res.json["message"] == "Order items must be updated via /orders"

    def test_update_product_not_in_check_returns_404(self):
        check_id = self.open_check()

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.ayran_id, "quantity": 1},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Product is not in this check"

    def test_update_nonexistent_check_returns_404(self):
        res = self.client.patch(
            "/checks/999",
            json={"product_id": self.water_id, "quantity": 1},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404
        assert res.json["message"] == "Check not found"

    def test_update_paid_check_returns_409(self):
        check_id = self.open_check()
        self.client.post(f"/checks/{check_id}/close", headers=self.get_auth_headers())

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.water_id, "quantity": 1},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 409
        assert res.json == {
            "error": "Conflict",
            "message": "Check is already paid",
            "code": 409,
        }

    def test_update_as_kitchen_staff_returns_403(self):
        check_id = self.open_check()

        res = self.client.patch(
            f"/checks/{check_id}",
            json={"product_id": self.water_id, "quantity": 1},
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    # POST /checks/<id>/close

    def test_close_check_snapshots_orders_and_frees_table(self):
        check_id = self.open_check()
        order_id = self.seed_order(
            [(self.kofte_id, 2, 180.0), (self.ayran_id, 1, 65.0)]
        )
        self.seed_order([(self.water_id, 5, 30.0)], status=OrderStatus.CANCELLED)

        res = self.client.post(
            f"/checks/{check_id}/close", headers=self.get_auth_headers()
        )

        assert res.status_code == 200
        data = res.json["data"]
        assert data["status"] == "paid"
        assert data["closed_at"].endswith("+00:00")
        assert data["total"] == 485.0
        assert [
            (p["product_id"], p["source"], p["order_id"]) for p in data["products"]
        ] == [
            (self.water_id, "check", None),
            (self.kofte_id, "order", order_id),
            (self.ayran_id, "order", order_id),
        ]

        check = db.session.get(Check, check_id)
        assert check.total == 485.0
        assert (
            db.session.query(CheckProduct)
            .filter_by(source=CheckProductSource.ORDER)
            .count()
            == 2
        )
        assert db.session.get(Table, self.table_id).status == TableStatus.AVAILABLE

    def test_closed_check_is_snapshot_of_prices(self):
        check_id = self.open_check()
        self.client.post(f"/checks/{check_id}/close", headers=self.get_auth_headers())
        db.session.get(Product, self.water_id).price = 999.0
        db.session.commit()

        res = self.client.get(f"/checks/{check_id}", headers=self.get_auth_headers())

        assert res.json["data"]["total"] == 60.0
        assert res.json["data"]["products"][0]["unit_price"] == 30.0

    def test_billed_orders_do_not_move_to_next_check(self):
        first_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)])
        self.client.post(f"/checks/{first_id}/close", headers=self.get_auth_headers())

        res = self.add_product(self.ayran_id)

        assert res.status_code == 201
        assert [p["source"] for p in res.json["data"]["products"]] == ["check"]
        assert res.json["data"]["total"] == 65.0

    def test_close_already_paid_check_returns_409(self):
        check_id = self.open_check()
        self.client.post(f"/checks/{check_id}/close", headers=self.get_auth_headers())

        res = self.client.post(
            f"/checks/{check_id}/close", headers=self.get_auth_headers()
        )

        assert res.status_code == 409
        assert res.json["message"] == "Check is already paid"

    def test_close_nonexistent_check_returns_404(self):
        res = self.client.post("/checks/999/close", headers=self.get_auth_headers())

        assert res.status_code == 404
        assert res.json["message"] == "Check not found"

    # POST /checks/<id>/cancel

    def test_cancel_check_returns_zero_total_without_products(self):
        check_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)])

        res = self.client.post(
            f"/checks/{check_id}/cancel", headers=self.get_auth_headers()
        )

        assert res.status_code == 200
        data = res.json["data"]
        assert data["status"] == "cancelled"
        assert data["total"] == 0.0
        assert data["closed_at"] is not None
        assert "products" not in data
        assert db.session.get(Table, self.table_id).status == TableStatus.AVAILABLE

    def test_cancelled_check_orders_do_not_move_to_next_check(self):
        first_id = self.open_check()
        self.seed_order([(self.kofte_id, 2, 180.0)])
        self.client.post(f"/checks/{first_id}/cancel", headers=self.get_auth_headers())

        res = self.add_product(self.ayran_id)

        assert res.json["data"]["total"] == 65.0

    def test_cancel_already_cancelled_check_returns_409(self):
        check_id = self.open_check()
        self.client.post(f"/checks/{check_id}/cancel", headers=self.get_auth_headers())

        res = self.client.post(
            f"/checks/{check_id}/cancel", headers=self.get_auth_headers()
        )

        assert res.status_code == 409
        assert res.json["message"] == "Check is already cancelled"

    def test_close_cancelled_check_returns_409(self):
        check_id = self.open_check()
        self.client.post(f"/checks/{check_id}/cancel", headers=self.get_auth_headers())

        res = self.client.post(
            f"/checks/{check_id}/close", headers=self.get_auth_headers()
        )

        assert res.status_code == 409
        assert res.json["message"] == "Check is already cancelled"

    def test_cancel_nonexistent_check_returns_404(self):
        res = self.client.post("/checks/999/cancel", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_cancel_as_kitchen_staff_returns_403(self):
        check_id = self.open_check()

        res = self.client.post(
            f"/checks/{check_id}/cancel",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403
