import pytest
from werkzeug.exceptions import NotFound

from flaskr.core.security import verify_password
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from flaskr.domains.user.services import UserService
from flaskr.domains.user.validators import UserCreateValidator
from tests.base import BaseTestCase


class TestUserService(BaseTestCase):
    domain_class = UserService
    domain: UserService

    def test_get_by_id_not_found(self):
        with self.app.test_request_context():
            with pytest.raises(NotFound) as exc_info:
                self.domain.get_by_id(55)

            assert exc_info.value.code == 404
            assert "There is no user" in exc_info.value.description

    def test_create_new_user(self):
        role = Role(name="admin")
        self.db.session.add(role)
        self.db.session.commit()

        with self.app.test_request_context():
            # The service expects validated data (password already hashed).
            test_data = UserCreateValidator().validate_data(
                {
                    "username": "denizbaba",
                    "password": "asd123",
                    "display_name": "BABA",
                    "email": "baba@gmail.com",
                    "role_id": 1,
                }
            )
            test_response = self.domain.create_new_user(data=test_data)
            assert test_response["id"] == 1
            assert test_response["username"] == "denizbaba"

            user = self.db.session.get(User, test_response["id"])
            assert verify_password(user.password, "asd123")
