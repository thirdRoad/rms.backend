from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from flaskr.core.extensions import db
from flaskr.core.security import hash_password, verify_password
from flaskr.domains.role.models import Role
from flaskr.domains.user.models import User
from flaskr.domains.user.services import UserService
from tests.base import BaseTestCase

VALID_USER = {
    "username": "denizbaba",
    "password": "asd123",
    "display_name": "BABA",
    "email": "baba@gmail.com",
}


class TestUserListAPI(BaseTestCase):
    domain_class = UserService
    domain: UserService

    def setup_case(self):
        role = Role(name="admin")
        db.session.add(role)
        db.session.commit()
        self.role_id = role.id

        admin_user = User(
            username="testadmin",
            password=hash_password("adminpass"),
            display_name="Admin",
            email="admin@test.com",
            role_id=self.role_id,
        )
        db.session.add(admin_user)
        db.session.commit()

    def get_auth_headers(self) -> dict:
        res = self.client.post(
            "/auth/login",
            json={"username": "testadmin", "password": "adminpass"},
        )
        token = res.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_user(self, **overrides: Any):
        payload = {**VALID_USER, "role_id": self.role_id, **overrides}
        return self.client.post(
            "/users/", json=payload, headers=self.get_auth_headers()
        )

    def patch_user(self, user_id: int, payload: Any):
        return self.client.patch(
            f"/users/{user_id}", json=payload, headers=self.get_auth_headers()
        )

    # --- create ---

    def test_create_user_returns_201(self):
        res = self.create_user()

        assert res.status_code == 201
        assert res.json["data"]["username"] == "denizbaba"
        assert res.json["data"]["email"] == "baba@gmail.com"
        assert "password" not in res.json["data"]

    def test_create_user_returns_400(self):
        res = self.client.post(
            "/users/",
            json={
                "username": "d",
                "password": "s",
                "display_name": "s",
                "email": "baba@",
            },
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["error"] == "Validation Error"
        assert res.json["message"] == {
            "username": ["Length must be between 3 and 32."],
            "password": ["Length must be between 6 and 128."],
            "display_name": ["Length must be between 3 and 16."],
            "email": ["Not a valid email address."],
            "role_id": ["Missing data for required field."],
        }
        assert res.json["code"] == 400

    def test_create_user_hashes_password_once(self):
        res = self.create_user()

        user = db.session.get(User, res.json["data"]["id"])
        assert user.password != "asd123"
        assert verify_password(user.password, "asd123")

    def test_created_user_can_login(self):
        self.create_user()

        res = self.client.post(
            "/auth/login", json={"username": "denizbaba", "password": "asd123"}
        )

        assert res.status_code == 200

    def test_create_user_normalizes_email_and_display_name(self):
        res = self.create_user(email="  Baba@Gmail.COM ", display_name="  BABA  ")

        assert res.status_code == 201
        assert res.json["data"]["email"] == "baba@gmail.com"
        assert res.json["data"]["display_name"] == "BABA"

    def test_create_user_invalid_username_returns_400(self):
        error = {"username": ["Only lowercase letters, digits, '_' and '.' allowed."]}

        for username in ["Deniz", "de niz", "  deniz  ", "deniz\n", "deniz!"]:
            res = self.create_user(username=username)

            assert res.status_code == 400, username
            assert res.json["message"] == error, username

    def test_create_user_blank_password_returns_400(self):
        res = self.create_user(password="      ")

        assert res.status_code == 400
        assert res.json["message"] == {"password": ["Password cannot be blank."]}

    def test_create_user_too_long_email_returns_400(self):
        res = self.create_user(email=f"{'a' * 60}@x.com")

        assert res.status_code == 400
        assert res.json["message"] == {"email": ["Longer than maximum length 64."]}

    def test_create_user_invalid_role_id_returns_400(self):
        res = self.create_user(role_id=0)

        assert res.status_code == 400
        assert res.json["message"] == {
            "role_id": ["Must be greater than or equal to 1."]
        }

    def test_create_user_non_string_value_returns_400(self):
        res = self.create_user(username=123, email=True)

        assert res.status_code == 400
        assert res.json["message"] == {
            "username": ["Not a valid string."],
            "email": ["Not a valid email address."],
        }

    def test_create_user_null_body_returns_400(self):
        res = self.client.post(
            "/users/",
            data="null",
            content_type="application/json",
            headers=self.get_auth_headers(),
        )

        assert res.status_code == 400
        assert res.json["message"] == {"_schema": ["Invalid input type."]}

    def test_create_user_unknown_field_returns_400(self):
        res = self.create_user(id=99)

        assert res.status_code == 400
        assert res.json["message"] == {"id": ["Unknown field."]}

    def test_create_user_duplicate_username_returns_409(self):
        self.create_user()

        res = self.create_user(display_name="Other", email="other@gmail.com")

        assert res.status_code == 409
        assert "already exists" in res.json["message"]

    def test_create_user_duplicate_email_returns_409(self):
        self.create_user()

        res = self.create_user(username="otheruser", display_name="Other")

        assert res.status_code == 409
        assert res.json["message"] == "Record already exists"

    # --- read / delete ---

    def test_get_all_users(self):
        res = self.client.get("/users/", headers=self.get_auth_headers())

        assert res.status_code == 200
        assert res.json["count"] == 1

    def test_get_specified_user(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.client.get(
            f"/users/{created_user_id}", headers=self.get_auth_headers()
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == created_user_id

    def test_get_nonexistent_user_returns_404(self):
        res = self.client.get("/users/999", headers=self.get_auth_headers())

        assert res.status_code == 404
        assert res.json["message"] == "User not found"

    def test_delete_user(self):
        user_res = self.client.get("/users/", headers=self.get_auth_headers()).json[
            "data"
        ][0]["id"]

        res = self.client.delete(f"/users/{user_res}", headers=self.get_auth_headers())

        assert res.status_code == 204

    # --- update ---

    def test_patch_user(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.patch_user(
            created_user_id,
            {
                "username": "refactored",
                "password": "sifre123",
                "display_name": "Samsun",
                "email": "samsun@gmail.com",
                "role_id": self.role_id,
            },
        )

        assert res.status_code == 200
        assert res.json["data"]["id"] == created_user_id
        assert res.json["data"]["username"] == "refactored"

    def test_patch_user_with_single_field(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.patch_user(created_user_id, {"display_name": "Samsun"})

        assert res.status_code == 200
        assert res.json["data"]["display_name"] == "Samsun"
        assert res.json["data"]["username"] == "denizbaba"
        assert res.json["data"]["email"] == "baba@gmail.com"

    def test_patch_user_with_empty_body_returns_400(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.patch_user(created_user_id, {})

        assert res.status_code == 400
        assert res.json["message"] == {
            "_schema": ["At least one field must be provided."]
        }

    def test_patch_user_password_is_hashed_and_usable(self):
        created_user_id = self.create_user().json["data"]["id"]

        self.patch_user(created_user_id, {"password": "newpass1"})

        user = db.session.get(User, created_user_id)
        assert verify_password(user.password, "newpass1")

        res = self.client.post(
            "/auth/login", json={"username": "denizbaba", "password": "newpass1"}
        )
        assert res.status_code == 200

    def test_patch_user_validates_sent_fields(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.patch_user(created_user_id, {"username": "Bad Name"})

        assert res.status_code == 400
        assert "username" in res.json["message"]

    def test_patch_user_duplicate_email_returns_409(self):
        created_user_id = self.create_user().json["data"]["id"]

        res = self.patch_user(created_user_id, {"email": "admin@test.com"})

        assert res.status_code == 409
        assert res.json["message"] == "Record already exists"

    def test_patch_nonexistent_user_returns_404(self):
        res = self.patch_user(999, {"display_name": "Samsun"})

        assert res.status_code == 404

    # --- list: filtering & sorting ---

    def seed_list_users(self) -> int:
        # testadmin (admin) already exists; adds ali, ayse (staff), mehmet (admin)
        staff = Role(name="staff")
        db.session.add(staff)
        db.session.commit()

        admin = db.session.scalars(select(User).filter_by(username="testadmin")).one()
        admin.created_at = datetime(2026, 10, 1, tzinfo=timezone.utc)

        for username, display_name, role_id, created_at in [
            ("ali", "Ali Veli", staff.id, datetime(2026, 11, 1, tzinfo=timezone.utc)),
            ("ayse", "Ayse Can", staff.id, datetime(2026, 11, 10, tzinfo=timezone.utc)),
            (
                "mehmet",
                "Mehmet Ali",
                self.role_id,
                datetime(2026, 11, 20, tzinfo=timezone.utc),
            ),
        ]:
            db.session.add(
                User(
                    username=username,
                    password=hash_password("secret1"),
                    display_name=display_name,
                    email=f"{username}@test.com",
                    role_id=role_id,
                    created_at=created_at,
                )
            )
        db.session.commit()
        return staff.id

    def list_users(self, **params: Any):
        return self.client.get(
            "/users/", query_string=params, headers=self.get_auth_headers()
        )

    def list_usernames(self, **params: Any) -> list[str]:
        res = self.list_users(**params)
        assert res.status_code == 200, res.json
        return [user["username"] for user in res.json["data"]]

    def test_list_without_params_is_ordered_by_id(self):
        self.seed_list_users()

        assert self.list_usernames() == ["testadmin", "ali", "ayse", "mehmet"]

    def test_filter_by_username_is_exact_match(self):
        self.seed_list_users()

        assert self.list_usernames(username="ali") == ["ali"]
        assert self.list_usernames(username="al") == []

    def test_filter_by_username_is_normalized(self):
        self.seed_list_users()

        assert self.list_usernames(username="  ALI ") == ["ali"]

    def test_filter_by_display_name_is_case_insensitive_contains(self):
        self.seed_list_users()

        assert self.list_usernames(display_name="ali") == ["ali", "mehmet"]

    def test_filter_by_display_name_escapes_wildcards(self):
        self.seed_list_users()

        assert self.list_usernames(display_name="%") == []

    def test_filter_by_email_is_normalized(self):
        self.seed_list_users()

        assert self.list_usernames(email=" AYSE@test.com ") == ["ayse"]

    def test_filter_by_role(self):
        staff_id = self.seed_list_users()

        assert self.list_usernames(role=staff_id) == ["ali", "ayse"]

    def test_multiple_filters_are_combined_with_and(self):
        self.seed_list_users()

        assert self.list_usernames(role=self.role_id, display_name="ali") == ["mehmet"]

    def test_empty_and_unknown_params_are_ignored(self):
        self.seed_list_users()

        assert len(self.list_usernames(username="", foo="bar")) == 4

    def test_filter_with_invalid_type_returns_400(self):
        res = self.list_users(role="abc")

        assert res.status_code == 400
        assert res.json["message"] == {"role": ["Not a valid integer."]}

    def test_sort_by_username_ascending(self):
        self.seed_list_users()

        assert self.list_usernames(sort="username") == [
            "ali",
            "ayse",
            "mehmet",
            "testadmin",
        ]

    def test_sort_by_username_descending(self):
        self.seed_list_users()

        assert self.list_usernames(sort="-username") == [
            "testadmin",
            "mehmet",
            "ayse",
            "ali",
        ]

    def test_sort_and_filter_together(self):
        staff_id = self.seed_list_users()

        assert self.list_usernames(role=staff_id, sort="-username") == [
            "ayse",
            "ali",
        ]

    def test_sort_by_disallowed_field_returns_400(self):
        res = self.list_users(sort="password")

        assert res.status_code == 400
        assert res.json["message"] == {
            "sort": [
                "Invalid sort field(s): password. "
                "Allowed: created_at, display_name, email, username."
            ]
        }

    def test_filter_by_created_from(self):
        self.seed_list_users()

        assert self.list_usernames(created_from="2026-11-10T00:00:00Z") == [
            "ayse",
            "mehmet",
        ]

    def test_filter_by_created_range(self):
        self.seed_list_users()

        result = self.list_usernames(
            created_from="2026-11-01T00:00:00Z", created_to="2026-11-10T00:00:00Z"
        )

        assert result == ["ali"]  # created_to is exclusive

    def test_filter_by_naive_datetime_returns_400(self):
        res = self.list_users(created_from="2026-11-01T00:00:00")

        assert res.status_code == 400
        assert "created_from" in res.json["message"]

    def test_sort_by_created_at_descending(self):
        self.seed_list_users()

        assert self.list_usernames(sort="-created_at") == [
            "mehmet",
            "ayse",
            "ali",
            "testadmin",
        ]
