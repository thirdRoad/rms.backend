from sqlalchemy import ColumnElement

from flaskr.core.extensions import db
from flaskr.core.security import hash_password
from flaskr.domains.role.models import Role
from flaskr.domains.table.models import Table, TableStatus
from flaskr.domains.table.repositories import TableRepository
from flaskr.domains.user.models import User
from flaskr.domains.user.repositories import UserRepository
from tests.base import BaseTestCase


class SampleUserRepository(UserRepository):
    def filter_has_role_name(self, value: str) -> ColumnElement[bool]:
        # custom condition through a relationship (not a plain column)
        return User.role.has(Role.name == value)


class TestBaseRepository(BaseTestCase):
    domain_class = SampleUserRepository
    domain: SampleUserRepository

    def setup_case(self):
        admin = Role(name="admin")
        staff = Role(name="staff")
        db.session.add_all([admin, staff])
        db.session.commit()

        for index, role in enumerate([admin, staff, staff, admin, staff]):
            db.session.add(
                User(
                    username=f"user{index}",
                    password=hash_password("secret1"),
                    display_name=f"User {index}",
                    email=f"user{index}@test.com",
                    role_id=role.id,
                )
            )
        db.session.commit()

    def usernames(self, users) -> list[str]:
        return [user.username for user in users]

    def test_custom_filter_method_is_used(self):
        users = self.domain.get_all(filters={"has_role_name__eq": "admin"})

        assert self.usernames(users) == ["user0", "user3"]

    def test_custom_and_column_filters_are_combined(self):
        users = self.domain.get_all(
            filters={"has_role_name__eq": "staff", "username__eq": "user2"}
        )

        assert self.usernames(users) == ["user2"]

    def test_in_filter_matches_any_value(self):
        staff_id = db.session.scalars(db.select(Role.id).filter_by(name="staff")).one()

        users = self.domain.get_all(filters={"role_id__in": [staff_id]})

        assert self.usernames(users) == ["user1", "user2", "user4"]

    def test_sort_with_equal_values_falls_back_to_id(self):
        users = self.domain.get_all(sort=["-role_id"])

        # staff (higher id) first, then admin; ties ordered by id
        assert self.usernames(users) == ["user1", "user2", "user4", "user0", "user3"]


class TestEnumColumnFilters(BaseTestCase):
    domain_class = TableRepository
    domain: TableRepository

    def setup_case(self):
        statuses = [
            TableStatus.AVAILABLE,
            TableStatus.OCCUPIED,
            TableStatus.RESERVED,
            TableStatus.OCCUPIED,
        ]
        db.session.add_all([Table(status=status) for status in statuses])
        db.session.commit()

    def table_ids(self, tables) -> list[int]:
        return [table.id for table in tables]

    def test_eq_with_enum_member(self):
        tables = self.domain.get_all(filters={"status__eq": TableStatus.OCCUPIED})

        assert self.table_ids(tables) == [2, 4]

    def test_in_with_enum_members(self):
        tables = self.domain.get_all(
            filters={"status__in": [TableStatus.AVAILABLE, TableStatus.RESERVED]}
        )

        assert self.table_ids(tables) == [1, 3]
