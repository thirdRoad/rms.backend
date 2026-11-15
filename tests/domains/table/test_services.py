import pytest
from werkzeug.exceptions import NotFound

from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.table.services import TableService
from tests.base import BaseTestCase


class TestTableService(BaseTestCase):
    domain_class = TableService
    domain: TableService

    def seed_table(self, status: TableStatus = TableStatus.AVAILABLE) -> int:
        table = Table(status=status)
        self.db.session.add(table)
        self.db.session.commit()
        return table.id

    def test_create_new_table(self):
        with self.app.test_request_context():
            new_table = self.domain.create_new_table()

            assert isinstance(new_table, Table)
            assert new_table.id == 1
            assert new_table.status == TableStatus.AVAILABLE
            assert new_table.last_updated is None

    def test_create_new_table_persists_to_db(self):
        with self.app.test_request_context():
            new_table = self.domain.create_new_table()

            assert self.db.session.get(Table, new_table.id) is not None

    def test_update_item_changes_status(self):
        table_id = self.seed_table()

        with self.app.test_request_context():
            test_response = self.domain.update_item(
                item_id=table_id, data=TableStatus.OCCUPIED
            )

            assert test_response["id"] == table_id
            assert test_response["status"] == "occupied"
            assert test_response["last_updated"] is not None

    def test_update_item_not_found(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.update_item(item_id=55, data=TableStatus.RESERVED)

            assert exc_info.value.code == 404
            assert "There is no item" in exc_info.value.description
