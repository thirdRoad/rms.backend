from typing import Any, Dict

from flaskr.core.base.services import BaseService
from flaskr.domains.user.models import User
from flaskr.domains.user.repositories import UserRepository


class UserService(BaseService):
    repository: UserRepository
    repository = UserRepository()
    domain = "User"

    def create_new_user(self, data: Dict[str, Any]) -> Dict | None:
        return self.create_new_item(
            model_class=User,
            column_name="username",
            unique_key=data["username"],
            **data,
        )
