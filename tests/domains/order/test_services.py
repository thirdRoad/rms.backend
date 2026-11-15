import pytest
from werkzeug.exceptions import BadRequest, NotFound

from flaskr.domains.category.models import Category
from flaskr.domains.order.models import Order
from flaskr.domains.order.services import OrderService
from flaskr.domains.order_item.models import OrderItem
from flaskr.domains.product.models import Product
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestOrdersService(BaseTestCase):
    domain_class = OrderService
    domain: OrderService

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

    def seed_user(
        self,
        username: str = "Efe",
        password: str = "efe123",
        display_name: str = "efe12",
        email: str = "efe@gmail.com",
    ) -> int:
        admin_role = Role(name="admin")
        self.db.session.add(admin_role)
        self.db.session.commit()
        user = User(
            username=username,
            password=password,
            display_name=display_name,
            email=email,
            role_id=admin_role.id,
        )
        self.db.session.add(user)
        self.db.session.commit()
        return user.id

    def seed_order(self):
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        product1 = self.seed_product()
        product2 = self.seed_product(
            c_name="Burger", p_name="Chicken Burger", price=10.0, stock=5
        )
        order = Order(user_id=user, table_id=table.id)
        self.db.session.add(order)
        self.db.session.commit()
        order_item1 = OrderItem(
            order_id=order.id, product_id=product1, quantity=1, unit_price=200
        )
        order_item2 = OrderItem(
            order_id=order.id, product_id=product2, quantity=20, unit_price=100
        )
        self.db.session.add_all([order_item1, order_item2])
        self.db.session.commit()
        return order.id

    def test_get_by_id_returns_item(self):
        order_id = self.seed_order()

        with self.app.test_request_context():
            result = self.domain.get_by_id(order_id)

            assert result["id"] == order_id
            assert result["user"]["id"] == 1
            assert result["user"]["username"] == "Efe"
            assert result["user"]["display_name"] == "efe12"
            assert result["user"]["email"] == "efe@gmail.com"

    def test_get_by_id_not_fount_returns_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.get_by_id(999)

            assert exc_info.value.code == 404

    def test_get_by_order_id_returns_all_serialized(self):
        order_id = self.seed_order()

        with self.app.test_request_context():
            result = self.domain.get_order_items(order_id=order_id)
            assert len(result) == 2
            assert {item["order_id"] for item in result} == {1}
            assert {item["product_id"] for item in result} == {1, 2}
            assert {item["quantity"] for item in result} == {1, 20}
            assert {item["unit_price"] for item in result} == {200, 100}

    def test_get_by_order_id_not_found_returns_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.get_order_items(999)

            assert exc_info.value.code == 404
            assert exc_info.value.description == "Order not found"

    def test_delete_order_products_returns_true_and_removes(self):
        order_id = self.seed_order()

        with self.app.test_request_context():
            assert self.domain.delete_order_products(item_id=order_id) is True

            with pytest.raises(NotFound) as exc_info:
                self.domain.get_order_items(order_id)

            assert exc_info.value.description == "Order has no items"

    def test_delete_order_products_nonexistent_item_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.delete_order_products(item_id=999)

    def test_create_new_order_return_serialize_data(self):
        product = self.seed_product()
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": user,
            "table_id": table.id,
            "items": [{"product_id": product, "quantity": 3}],
        }
        with self.app.test_request_context():
            result = self.domain.create_new_order(data)

            assert result["id"] == 1

    def test_create_new_order_user_is_none_return_nonexistent_item_raises_404(self):
        product = self.seed_product()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": None,
            "table_id": table.id,
            "items": [{"product_id": product, "quantity": 3}],
        }
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.create_new_order(data)

    def test_create_new_order_table_is_none_return_nonexistent_item_raises_404(self):
        product = self.seed_product()
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": user,
            "table_id": None,
            "items": [{"product_id": product, "quantity": 3}],
        }
        with self.app.test_request_context():
            with pytest.raises(NotFound):
                self.domain.create_new_order(data)

    def test_create_new_order_persists_to_db(self):
        product = self.seed_product()
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": user,
            "table_id": table.id,
            "items": [{"product_id": product, "quantity": 3}],
        }
        with self.app.test_request_context():
            self.domain.create_new_order(data)

        saved = self.db.session.query(Order).filter_by(id="1").one_or_none()
        assert saved is not None

    def test_create_new_order_with_nonexistent_product_raises_404(self):
        product = self.seed_product()
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": user,
            "table_id": table.id,
            "items": [
                {"product_id": product, "quantity": 1},
                {"product_id": 999, "quantity": 2},
            ],
        }
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.create_new_order(data)

            assert exc_info.value.description == "Product not found: [999]"

        assert self.db.session.query(Order).count() == 0

    def test_create_new_order_with_duplicate_product_raises_400(self):
        product = self.seed_product()
        user = self.seed_user()
        table = Table()
        self.db.session.add(table)
        self.db.session.commit()
        data = {
            "user_id": user,
            "table_id": table.id,
            "items": [
                {"product_id": product, "quantity": 1},
                {"product_id": product, "quantity": 2},
            ],
        }
        with self.app.test_request_context():
            with pytest.raises(BadRequest) as exc_info:
                self.domain.create_new_order(data)

            assert (
                exc_info.value.description
                == f"Duplicate product_id in items: [{product}]"
            )

        assert self.db.session.query(Order).count() == 0

    def test_update_order_items_replaces_items_with_given_list(self):
        order_id = self.seed_order()  # product 1 x1, product 2 x20
        new_product = self.seed_product(c_name="Drinks", p_name="Cola", price=40.0)

        with self.app.test_request_context():
            result = self.domain.update_order_items(
                order_id=order_id,
                items=[
                    {"product_id": 1, "quantity": 3},
                    {"product_id": new_product, "quantity": 2},
                ],
            )

        quantities = {item["product_id"]: item["quantity"] for item in result}
        assert quantities == {1: 3, new_product: 2}

        assert self.db.session.get(OrderItem, (order_id, 2)) is None
        assert self.db.session.get(OrderItem, (order_id, 1)).unit_price == 200
        assert self.db.session.get(OrderItem, (order_id, new_product)).unit_price == 40

    def test_update_order_items_nonexistent_order_raises_404(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.update_order_items(
                    order_id=999, items=[{"product_id": 1, "quantity": 3}]
                )

            assert exc_info.value.description == "Order not found"

    def test_update_order_items_nonexistent_product_raises_404_and_changes_nothing(
        self,
    ):
        order_id = self.seed_order()

        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.update_order_items(
                    order_id=order_id,
                    items=[
                        {"product_id": 1, "quantity": 9},
                        {"product_id": 999, "quantity": 1},
                    ],
                )

            assert exc_info.value.description == "Product not found: [999]"

        assert self.db.session.get(OrderItem, (order_id, 1)).quantity == 1
        assert self.db.session.get(OrderItem, (order_id, 2)) is not None

    def test_update_order_items_duplicate_product_raises_400(self):
        order_id = self.seed_order()

        with self.app.test_request_context():
            with pytest.raises(BadRequest):
                self.domain.update_order_items(
                    order_id=order_id,
                    items=[
                        {"product_id": 1, "quantity": 2},
                        {"product_id": 1, "quantity": 5},
                    ],
                )
