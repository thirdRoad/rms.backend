from werkzeug.security import generate_password_hash

from flaskr.core.extensions import db
from flaskr.domains.auth.models import TokenBlocklist
from flaskr.domains.auth.services import AuthService
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestAuthAPI(BaseTestCase):
    domain_class = AuthService
    domain: AuthService

    def setup_case(self):
        admin_role = Role(name="admin")
        kitchen_role = Role(name="kitchen_staff")
        waiter_role = Role(name="waiter")
        db.session.add_all([admin_role, kitchen_role, waiter_role])
        db.session.commit()

        users = [
            User(
                username="testadmin",
                password=generate_password_hash("adminpass"),
                display_name="Admin",
                email="admin@test.com",
                role_id=admin_role.id,
            ),
            User(
                username="testwaiter",
                password=generate_password_hash("waiterpass"),
                display_name="Waiter",
                email="waiter@test.com",
                role_id=waiter_role.id,
            ),
        ]
        db.session.add_all(users)
        db.session.commit()
        self.admin_id = users[0].id

    def login(self, username: str = "testadmin", password: str = "adminpass"):
        return self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )

    def get_auth_headers(
        self, username: str = "testadmin", password: str = "adminpass"
    ) -> dict:
        token = self.login(username, password).json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_login_success_returns_tokens(self):
        res = self.login()

        assert res.status_code == 200
        assert "access_token" in res.json["data"]
        assert res.json["data"]["access_token"]
        assert "refresh_token" in res.json["data"]
        assert "server_time" in res.json

    def test_login_wrong_password_returns_401(self):
        res = self.login(password="wrongpass")

        assert res.status_code == 401
        assert "Invalid credentials" in res.json["message"]

    def test_login_nonexistent_user_returns_401(self):
        res = self.login(username="ghostuser", password="whatever1")

        assert res.status_code == 401

        assert "Invalid credentials" in res.json["message"]

    def test_login_short_username_returns_400(self):
        res = self.login(username="ab")

        assert res.status_code == 400
        assert res.json["error"] == "Validation Error"
        assert "username" in res.json["message"]

    def test_login_missing_password_returns_400(self):
        res = self.client.post("/auth/login", json={"username": "testadmin"})

        assert res.status_code == 400
        assert "password" in res.json["message"]

    def test_logout_returns_success_message(self):
        res = self.client.post("/auth/logout", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["data"]["msg"] == "Successfully logged out"

    def test_logout_adds_token_to_blocklist(self):
        headers = self.get_auth_headers()

        assert db.session.query(TokenBlocklist).count() == 0

        self.client.post("/auth/logout", headers=headers)

        assert db.session.query(TokenBlocklist).count() == 1

    def test_logout_revokes_token(self):
        headers = self.get_auth_headers()

        res = self.client.get("/auth/me", headers=headers)
        assert res.status_code == 200

        self.client.post("/auth/logout", headers=headers)

        res = self.client.get("/auth/me", headers=headers)
        assert res.status_code == 401

    def test_logout_without_token_returns_401(self):
        res = self.client.post("/auth/logout")

        assert res.status_code == 401

    def test_me_returns_current_user(self):
        res = self.client.get("/auth/me", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["data"]["id"] == self.admin_id
        assert res.json["data"]["username"] == "testadmin"
        assert "password" not in res.json["data"]

    def test_me_without_token_returns_401(self):
        res = self.client.get("/auth/me")

        assert res.status_code == 401

    def test_me_with_unauthorized_role_returns_403(self):

        res = self.client.get(
            "/auth/me",
            headers=self.get_auth_headers("testwaiter", "waiterpass"),
        )

        assert res.status_code == 403

    def test_me_with_malformed_token_returns_401(self):
        res = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not.a.real.token"},
        )

        assert res.status_code == 401
        assert res.json == {
            "error": "Unauthorized",
            "message": "Invalid token",
            "code": 401,
        }

    def test_me_without_token_returns_standard_error_format(self):
        res = self.client.get("/auth/me")

        assert res.json == {
            "error": "Unauthorized",
            "message": "Missing authorization token",
            "code": 401,
        }

    def test_me_with_revoked_token_returns_standard_error_format(self):
        headers = self.get_auth_headers()
        self.client.post("/auth/logout", headers=headers)

        res = self.client.get("/auth/me", headers=headers)

        assert res.json == {
            "error": "Unauthorized",
            "message": "Token has been revoked",
            "code": 401,
        }

    def test_login_with_uppercase_username_returns_401(self):
        res = self.login(username="TestAdmin")

        assert res.status_code == 401
        assert res.json["message"] == "Invalid credentials"

    def test_login_with_null_body_returns_400(self):
        res = self.client.post(
            "/auth/login", data="null", content_type="application/json"
        )

        assert res.status_code == 400
        assert res.json["message"] == {"_schema": ["Invalid input type."]}

    def test_login_with_non_string_username_returns_400(self):
        res = self.client.post(
            "/auth/login", json={"username": 12345, "password": "adminpass"}
        )

        assert res.status_code == 400
        assert res.json["message"] == {"username": ["Not a valid string."]}
