from sqlalchemy.exc import SQLAlchemyError
from typing_extensions import override

from flaskr.core.base.repositories import BaseRepository
from flaskr.core.extensions import db
from flaskr.core.utils import utc_now
from flaskr.domains.table.models import Table, TableStatus


class TableRepository(BaseRepository):
    model = Table

    @override
    def update(self, item_id: int, data: TableStatus) -> bool:
        entity = db.session.get(self.model, item_id)
        entity.status = data
        entity.last_updated = utc_now()
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        return True
