from typing import Any, Dict, List, Tuple

from flask import abort
from typing_extensions import override

from flaskr.core.base.services import BaseService
from flaskr.core.utils import utc_now
from flaskr.domains.check.models import (
    Check,
    CheckProduct,
    CheckProductSource,
    CheckStatus,
)
from flaskr.domains.check.repositories import CheckRepository
from flaskr.domains.product.repositories import ProductRepository
from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.table.repositories import TableRepository

DEFAULT_SORT = ["-created_at"]


class CheckService(BaseService):
    repository: CheckRepository
    repository = CheckRepository()
    product_repo = ProductRepository()
    table_repo = TableRepository()

    def get_check(self, check_id: int) -> Check:
        check = self.repository.get_by_id(item_id=check_id)
        if check is None:
            abort(404, description="Check not found")
        return check

    @staticmethod
    def ensure_open(check: Check) -> None:
        if check.status != CheckStatus.OPEN:
            abort(409, description=f"Check is already {check.status.value}")

    @staticmethod
    def set_table_status(table: Table, status: TableStatus) -> None:
        table.status = status
        table.last_updated = utc_now()

    @staticmethod
    def calculate_total(products: List[Dict[str, Any]]) -> float:
        return round(sum(p["quantity"] * p["unit_price"] for p in products), 2)

    def order_products(self, check: Check) -> List[Dict[str, Any]]:
        return [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source": CheckProductSource.ORDER.value,
                "order_id": item.order_id,
            }
            for item in self.repository.get_unbilled_order_items(check.table_id)
        ]

    def products_of(self, check: Check) -> List[Dict[str, Any]]:
        products = [product.serialize for product in check.products]
        if check.status == CheckStatus.OPEN:  # closed checks are snapshots
            products += self.order_products(check)
        return products

    def summary(self, check: Check) -> Dict[str, Any]:
        response = check.serialize
        if check.status == CheckStatus.OPEN:
            response["total"] = self.calculate_total(self.products_of(check))
        return response

    def detail(self, check: Check) -> Dict[str, Any]:
        products = self.products_of(check)
        response = check.serialize
        if check.status == CheckStatus.OPEN:
            response["total"] = self.calculate_total(products)
        response["products"] = products
        return response

    @override
    def get_by_id(self, item_id: int) -> Dict[str, Any]:
        return self.detail(self.get_check(check_id=item_id))

    @override
    def list_items(
        self, filters: None | Dict[str, Any] = None, sort: None | List[str] = None
    ) -> List[Dict[str, Any]]:
        checks = self.repository.get_all(filters=filters, sort=sort or DEFAULT_SORT)
        return [self.summary(check) for check in checks]

    def add_product(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        table = self.table_repo.get_by_id(item_id=data["table_id"])
        if table is None:
            abort(404, description="Table not found")

        product = self.product_repo.get_by_id(item_id=data["product_id"])
        if product is None:
            abort(404, description="Product not found")

        check = self.repository.get_open_by_table(table_id=table.id)
        is_new = check is None
        if is_new:
            check = Check(table_id=table.id)
            self.set_table_status(table, TableStatus.OCCUPIED)

        if item := self.find_direct_product(check, product.id):
            item.quantity += data["quantity"]
        else:
            check.products.append(
                CheckProduct(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=data["quantity"],
                    unit_price=product.price,
                    source=CheckProductSource.CHECK,
                )
            )

        self.repository.save(check)
        return self.detail(check), is_new

    @staticmethod
    def find_direct_product(check: Check, product_id: int) -> None | CheckProduct:
        return next(
            (
                product
                for product in check.products
                if product.source == CheckProductSource.CHECK
                and product.product_id == product_id
            ),
            None,
        )

    def update_product(self, check_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        check = self.get_check(check_id=check_id)
        self.ensure_open(check)

        item = self.find_direct_product(check, data["product_id"])
        if item is None:
            order_product_ids = {p["product_id"] for p in self.order_products(check)}
            if data["product_id"] in order_product_ids:
                abort(409, description="Order items must be updated via /orders")
            abort(404, description="Product is not in this check")

        if data["quantity"] == 0:
            check.products.remove(item)
        else:
            item.quantity = data["quantity"]

        self.repository.save(check)
        return self.detail(check)

    def snapshot_order_products(self, check: Check) -> None:
        for product in self.order_products(check):
            check.products.append(
                CheckProduct(
                    product_id=product["product_id"],
                    product_name=product["product_name"],
                    quantity=product["quantity"],
                    unit_price=product["unit_price"],
                    source=CheckProductSource.ORDER,
                    order_id=product["order_id"],
                )
            )

    def finish_check(self, check: Check, status: CheckStatus, total: float) -> None:
        check.status = status
        check.total = total
        check.closed_at = utc_now()
        self.set_table_status(check.table, TableStatus.AVAILABLE)
        self.repository.save(check)

    def close_check(self, check_id: int) -> Dict[str, Any]:  # payment
        check = self.get_check(check_id=check_id)
        self.ensure_open(check)

        self.snapshot_order_products(check)
        total = self.calculate_total([p.serialize for p in check.products])
        self.finish_check(check, status=CheckStatus.PAID, total=total)
        return self.detail(check)

    def cancel_check(self, check_id: int) -> Dict[str, Any]:
        check = self.get_check(check_id=check_id)
        self.ensure_open(check)

        # orders are still snapshotted so they do not move to the next check
        self.snapshot_order_products(check)
        self.finish_check(check, status=CheckStatus.CANCELLED, total=0.0)
        return check.serialize
