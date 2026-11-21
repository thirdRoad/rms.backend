from typing import Any, Dict

from flask import abort

from flaskr.core.base.services import BaseService
from flaskr.domains.user.models import User
from flaskr.domains.user.repositories import UserRepository


class UserService(BaseService):
    repository: UserRepository
    repository = UserRepository()

    def get_by_id(self, item_id: int) -> Dict[str, Any]:
        user = self.repository.get_by_id(item_id=item_id)

        if user is None:
            abort(404, description="There is no user")

        response = user.serialize
        response["role"] = {"id": user.role.id, "name": user.role.name}
        return response

    def create_new_user(self, data: Dict[str, Any]) -> Dict | None:
        return self.create_new_item(
            model_class=User,
            column_name="username",
            unique_key=data["username"],
            **data,
        )
