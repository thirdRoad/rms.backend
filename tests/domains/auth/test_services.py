import pytest
from flask_jwt_extended import decode_token, verify_jwt_in_request
from werkzeug.exceptions import Unauthorized

from flaskr.core.security import hash_password
from flaskr.domains.auth.models import TokenBlocklist
from flaskr.domains.auth.services import AuthService
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestAuthService(BaseTestCase):
    domain_class = AuthService
    domain: AuthService

    def setup_case(self):
        role = Role(name="admin")
        self.db.session.add(role)
        self.db.session.commit()

        user = User(
            username="testadmin",
            password=hash_password("adminpass"),
            display_name="Admin",
            email="admin@test.com",
            role_id=role.id,
        )
        self.db.session.add(user)
        self.db.session.commit()
        self.user_id = user.id

    def test_verify_user_returns_tokens(self):
        with self.app.test_request_context():
            result = self.domain.verify_user(username="testadmin", password="adminpass")

            assert "access_token" in result
            assert result["access_token"]
            assert "refresh_token" in result

    def test_verify_user_token_contains_identity_and_role(self):
        with self.app.test_request_context():
            result = self.domain.verify_user(username="testadmin", password="adminpass")

            claims = decode_token(result["access_token"])
            assert claims["sub"] == str(self.user_id)
            assert claims["role"] == "admin"

    def test_verify_user_wrong_password_raises_401(self):
        with self.app.test_request_context():
            with pytest.raises(Unauthorized) as exc_info:
                self.domain.verify_user(username="testadmin", password="wrongpass")

            assert exc_info.value.code == 401
            assert "Invalid credentials" in exc_info.value.description

    def test_verify_user_nonexistent_user_raises_401(self):

        with self.app.test_request_context():
            with pytest.raises(Unauthorized) as exc_info:
                self.domain.verify_user(username="ghostuser", password="whatever1")

            assert exc_info.value.code == 401
            assert "Invalid credentials" in exc_info.value.description

    def test_logout_adds_jti_to_blocklist(self):
        with self.app.test_request_context():
            token = self.domain.verify_user(username="testadmin", password="adminpass")[
                "access_token"
            ]
            expected_jti = decode_token(token)["jti"]

        with self.app.test_request_context(
            headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            self.domain.logout()

        entries = self.db.session.query(TokenBlocklist).all()
        assert len(entries) == 1
        assert entries[0].jti == expected_jti
        assert entries[0].created_at is not None
