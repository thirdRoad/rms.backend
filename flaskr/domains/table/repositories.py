from typing import Any

from typing_extensions import override

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.utils import utc_now
from flaskr.domains.table.models import Table


class TableRepository(BaseRepository):
    model = Table

    @override
    def update(self, item_id: int, data: dict[str, Any]) -> bool:
        return super().update(item_id=item_id, data={**data, "last_updated": utc_now()})
