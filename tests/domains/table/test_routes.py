from werkzeug.security import generate_password_hash

from flaskr.core.extensions import db
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.table.services import TableService
from flaskr.domains.user.models import User
from tests.base import BaseTestCase


class TestTableListAPI(BaseTestCase):
    domain_class = TableService
    domain: TableService

    def setup_case(self):
        admin_role = Role(name="admin")
        service_role = Role(name="service_staff")
        kitchen_role = Role(name="kitchen_staff")
        waiter_role = Role(name="waiter")
        db.session.add_all([admin_role, service_role, kitchen_role, waiter_role])
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
                username="testservice",
                password=generate_password_hash("servicepass"),
                display_name="Service",
                email="service@test.com",
                role_id=service_role.id,
            ),
            User(
                username="testkitchen",
                password=generate_password_hash("kitchenpass"),
                display_name="Kitchen",
                email="kitchen@test.com",
                role_id=kitchen_role.id,
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

    def get_auth_headers(
        self, username: str = "testadmin", password: str = "adminpass"
    ) -> dict:
        res = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        token = res.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_table(self, status: TableStatus = TableStatus.AVAILABLE) -> int:
        table = Table(status=status)
        db.session.add(table)
        db.session.commit()
        return table.id

    def test_create_table_returns_201(self):
        res = self.client.post("/tables/", headers=self.get_auth_headers())

        assert res.status_code == 201
        assert res.json["data"]["status"] == "available"
        assert isinstance(res.json["data"]["id"], int)
        assert res.json["data"]["created_at"]
        assert res.json["data"]["last_updated"] is None

    def test_create_table_persists_to_db(self):
        res = self.client.post("/tables/", headers=self.get_auth_headers())
        created_table_id = res.json["data"]["id"]

        assert db.session.get(Table, created_table_id) is not None

    def test_create_table_without_token_returns_401(self):
        res = self.client.post("/tables/")

        assert res.status_code == 401

    def test_create_table_as_service_staff_returns_403(self):
        res = self.client.post(
            "/tables/",
            headers=self.get_auth_headers("testservice", "servicepass"),
        )

        assert res.status_code == 403

    def test_get_all_tables(self):
        self.create_table()
        self.create_table(status=TableStatus.OCCUPIED)

        res = self.client.get("/tables/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 2
        assert {item["status"] for item in res.json["data"]} == {
            "available",
            "occupied",
        }

    def test_get_all_tables_empty_returns_zero_count(self):
        res = self.client.get("/tables/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 0
        assert res.json["data"] == []

    def test_get_all_tables_as_kitchen_staff_returns_200(self):
        res = self.client.get(
            "/tables/",
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 200

    def test_get_all_tables_as_waiter_returns_403(self):
        res = self.client.get(
            "/tables/",
            headers=self.get_auth_headers("testwaiter", "waiterpass"),
        )

        assert res.status_code == 403

    def test_get_all_tables_without_token_returns_401(self):
        res = self.client.get("/tables/")

        assert res.status_code == 401

    def test_get_specified_table(self):
        table_id = self.create_table(status=TableStatus.RESERVED)

        res = self.client.get(f"/tables/{table_id}", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["data"]["id"] == table_id
        assert res.json["data"]["status"] == "reserved"

    def test_get_nonexistent_table_returns_404(self):
        res = self.client.get("/tables/55", headers=self.get_auth_headers())

        assert res.status_code == 404
        assert "There is no item" in res.json["message"]

    def test_get_specified_table_as_waiter_returns_403(self):
        table_id = self.create_table()

        res = self.client.get(
            f"/tables/{table_id}",
            headers=self.get_auth_headers("testwaiter", "waiterpass"),
        )

        assert res.status_code == 403

    def test_patch_table(self):
        table_id = self.create_table()

        res = self.client.patch(
            f"/tables/{table_id}",
            json={"status": "occupied"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == table_id
        assert res.json["data"]["status"] == "occupied"
        assert res.json["data"]["last_updated"] is not None

    def test_patch_table_as_service_staff_returns_200(self):
        table_id = self.create_table()

        res = self.client.patch(
            f"/tables/{table_id}",
            json={"status": "reserved"},
            headers=self.get_auth_headers("testservice", "servicepass"),
        )

        assert res.status_code == 200
        assert res.json["data"]["status"] == "reserved"

    def test_patch_table_invalid_status_returns_400(self):
        table_id = self.create_table()

        res = self.client.patch(
            f"/tables/{table_id}",
            json={"status": "flying"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["error"] == "Validation Error"
        assert res.json["message"] == {
            "status": ["Must be one of: available, reserved, occupied."]
        }
        assert res.json["code"] == 400

    def test_patch_table_missing_status_returns_400(self):
        table_id = self.create_table()

        res = self.client.patch(
            f"/tables/{table_id}",
            json={},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["message"] == {"status": ["Missing data for required field."]}

    def test_patch_nonexistent_table_returns_404(self):
        res = self.client.patch(
            "/tables/55",
            json={"status": "occupied"},
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 404

    def test_patch_table_as_kitchen_staff_returns_403(self):
        table_id = self.create_table()

        res = self.client.patch(
            f"/tables/{table_id}",
            json={"status": "occupied"},
            headers=self.get_auth_headers("testkitchen", "kitchenpass"),
        )

        assert res.status_code == 403

    def test_patch_table_without_token_returns_401(self):
        table_id = self.create_table()

        res = self.client.patch(f"/tables/{table_id}", json={"status": "occupied"})

        assert res.status_code == 401

    def test_delete_table(self):
        table_id = self.create_table()

        res = self.client.delete(f"/tables/{table_id}", headers=self.get_auth_headers())

        assert res.status_code == 204

        get_res = self.client.get(
            f"/tables/{table_id}", headers=self.get_auth_headers()
        )
        assert get_res.status_code == 404

    def test_delete_nonexistent_table_returns_404(self):
        res = self.client.delete("/tables/55", headers=self.get_auth_headers())

        assert res.status_code == 404

    def test_delete_table_as_service_staff_returns_403(self):
        table_id = self.create_table()

        res = self.client.delete(
            f"/tables/{table_id}",
            headers=self.get_auth_headers("testservice", "servicepass"),
        )

        assert res.status_code == 403

    def test_delete_table_without_token_returns_401(self):
        table_id = self.create_table()

        res = self.client.delete(f"/tables/{table_id}")

        assert res.status_code == 401
