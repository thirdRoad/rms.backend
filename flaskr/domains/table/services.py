from typing import Any, Dict

from flaskr.core.base.services import BaseService
from flaskr.domains.table.models import Table
from flaskr.domains.table.repositories import TableRepository


class TableService(BaseService):
    repository: TableRepository
    repository = TableRepository()

    def create_new_table(self, data: Dict[str, Any]) -> Table:
        return self.repository.add(Table(**data))
