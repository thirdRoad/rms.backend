import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict, NotFound

from flaskr.core.extensions import db
from flaskr.domains.category.models import Category
from flaskr.domains.check.models import Check, CheckStatus
from flaskr.domains.check.services import CheckService
from flaskr.domains.order.models import Order
from flaskr.domains.order_item.models import OrderItem
from flaskr.domains.product.models import Product
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestCheckService(BaseTestCase):
    domain_class = CheckService
    domain: CheckService

    def setup_case(self):
        role = Role(name="admin")
        db.session.add(role)
        db.session.commit()
        user = User(
            username="efe",
            password="efe123",
            display_name="efe12",
            email="efe@gmail.com",
            role_id=role.id,
        )
        table = Table()
        category = Category(name="Drinks")
        db.session.add_all([user, table, category])
        db.session.commit()
        product = Product(name="Cola", price=40.0, stock=5, category_id=category.id)
        db.session.add(product)
        db.session.commit()

        self.user_id = user.id
        self.table_id = table.id
        self.product_id = product.id

    def seed_order(self, quantity: int = 2, unit_price: float = 35.0) -> int:
        order = Order(user_id=self.user_id, table_id=self.table_id)
        db.session.add(order)
        db.session.commit()
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=self.product_id,
                quantity=quantity,
                unit_price=unit_price,
            )
        )
        db.session.commit()
        return order.id

    def add(self, quantity: int = 1) -> tuple[dict, bool]:
        return self.domain.add_product(
            {
                "table_id": self.table_id,
                "product_id": self.product_id,
                "quantity": quantity,
            }
        )

    def test_add_product_opens_check_and_occupies_table(self):
        with self.app.test_request_context():
            result, is_new = self.add(quantity=2)

        assert is_new is True
        assert result["status"] == "open"
        assert result["total"] == 80.0
        assert db.session.get(Table, self.table_id).status == TableStatus.OCCUPIED
        assert db.session.get(Table, self.table_id).last_updated is not None

    def test_add_product_reuses_open_check(self):
        with self.app.test_request_context():
            first, _ = self.add()
            second, is_new = self.add(quantity=4)

        assert is_new is False
        assert second["id"] == first["id"]
        assert second["products"][0]["quantity"] == 5

    def test_add_product_unknown_table_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.add_product(
                    {"table_id": 999, "product_id": self.product_id, "quantity": 1}
                )

        assert exc_info.value.description == "Table not found"

    def test_same_product_from_check_and_order_kept_separately(self):
        order_id = self.seed_order(quantity=2, unit_price=35.0)

        with self.app.test_request_context():
            check, _ = self.add(quantity=1)

        assert [(p["source"], p["order_id"]) for p in check["products"]] == [
            ("check", None),
            ("order", order_id),
        ]
        assert check["total"] == 110.0  # order keeps its own unit price

    def test_update_product_on_order_only_product_raises_409(self):
        with self.app.test_request_context():
            check, _ = self.add()
            self.domain.update_product(
                check["id"], {"product_id": self.product_id, "quantity": 0}
            )
            self.seed_order()

            with pytest.raises(Conflict) as exc_info:
                self.domain.update_product(
                    check["id"], {"product_id": self.product_id, "quantity": 3}
                )

        assert exc_info.value.description == "Order items must be updated via /orders"

    def test_close_check_uses_order_item_unit_price(self):
        self.seed_order(quantity=2, unit_price=35.0)
        db.session.get(Product, self.product_id).price = 50.0
        db.session.commit()

        with self.app.test_request_context():
            check, _ = self.add(quantity=1)
            result = self.domain.close_check(check["id"])

        assert result["total"] == 120.0  # 1 x 50 (check) + 2 x 35 (order)
        assert db.session.get(Check, check["id"]).total == 120.0

    def test_close_check_unknown_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.close_check(999)

        assert exc_info.value.description == "Check not found"

    def test_cancel_check_sets_zero_total(self):
        self.seed_order()

        with self.app.test_request_context():
            check, _ = self.add()
            result = self.domain.cancel_check(check["id"])

        assert result["status"] == "cancelled"
        assert result["total"] == 0.0
        assert db.session.get(Table, self.table_id).status == TableStatus.AVAILABLE

    def test_list_items_defaults_to_newest_first(self):
        with self.app.test_request_context():
            first, _ = self.add()
            self.domain.close_check(first["id"])
            second, _ = self.add()

            result = self.domain.list_items()

        assert [c["id"] for c in result] == [second["id"], first["id"]]

    def test_second_open_check_for_table_is_rejected_by_db(self):
        db.session.add(Check(table_id=self.table_id))
        db.session.commit()

        db.session.add(Check(table_id=self.table_id, status=CheckStatus.OPEN))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(Check(table_id=self.table_id, status=CheckStatus.PAID))
        db.session.commit()
        assert db.session.query(Check).count() == 2
