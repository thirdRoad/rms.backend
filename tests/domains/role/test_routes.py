from flaskr.core.extensions import db
from flaskr.core.security import hash_password
from flaskr.domains.role.models import Role
from flaskr.domains.role.services import RoleService
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestRoleListAPI(BaseTestCase):
    domain_class = RoleService
    domain: RoleService

    def setup_case(self):
        admin_role = Role(name="admin")
        service_role = Role(name="service_staff")
        kitchen_role = Role(name="kitchen_staff")
        db.session.add_all([admin_role, service_role, kitchen_role])
        db.session.commit()

        users = [
            User(
                username="testadmin",
                password=hash_password("adminpass"),
                display_name="Admin",
                email="admin@test.com",
                role_id=admin_role.id,
            ),
            User(
                username="testservice",
                password=hash_password("servicepass"),
                display_name="Service",
                email="service@test.com",
                role_id=service_role.id,
            ),
        ]
        db.session.add_all(users)
        db.session.commit()

    def get_auth_headers(
        self, username: str = "testadmin", password: str = "adminpass"
    ) -> dict:
        res = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        token = res.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_all_roles(self):
        res = self.client.get("/roles/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 3
        assert {item["name"] for item in res.json["data"]} == {
            "admin",
            "service_staff",
            "kitchen_staff",
        }

    def test_get_all_roles_returns_only_id_and_name(self):
        res = self.client.get("/roles/", headers=self.get_auth_headers())

        assert res.status_code == 200
        for item in res.json["data"]:
            assert set(item.keys()) == {"id", "name"}

    def test_get_all_roles_contains_created_role(self):
        new_role = Role(name="cashier")
        db.session.add(new_role)
        db.session.commit()

        res = self.client.get("/roles/", headers=self.get_auth_headers())

        assert res.json["count"] == 4
        assert {"id": new_role.id, "name": "cashier"} in res.json["data"]

    def test_get_all_roles_without_token_returns_401(self):
        res = self.client.get("/roles/")

        assert res.status_code == 401

    def test_get_all_roles_as_service_staff_returns_403(self):
        res = self.client.get(
            "/roles/",
            headers=self.get_auth_headers("testservice", "servicepass"),
        )

        assert res.status_code == 403
        assert res.json["message"] == "Forbidden"

    def test_post_role_returns_405(self):
        res = self.client.post(
            "/roles/",
            json={"name": "cashier"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 405
