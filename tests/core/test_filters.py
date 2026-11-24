from sqlalchemy import column

from flaskr.core.base.filters import Lookup


class TestLookup:
    def test_eq(self):
        assert str(Lookup.EQ.apply(column("age"), 3)) == "age = :age_1"

    def test_gte(self):
        assert str(Lookup.GTE.apply(column("age"), 3)) == "age >= :age_1"

    def test_lte(self):
        assert str(Lookup.LTE.apply(column("age"), 3)) == "age <= :age_1"

    def test_gt(self):
        assert str(Lookup.GT.apply(column("age"), 3)) == "age > :age_1"

    def test_lt(self):
        assert str(Lookup.LT.apply(column("age"), 3)) == "age < :age_1"

    def test_in(self):
        condition = str(Lookup.IN.apply(column("status"), ["a", "b"]))

        assert condition == "status IN (__[POSTCOMPILE_status_1])"

    def test_icontains_is_case_insensitive_like(self):
        condition = str(Lookup.ICONTAINS.apply(column("name"), "den")).lower()

        assert "lower(name) like" in condition

    def test_lookup_is_created_from_string(self):
        assert Lookup("icontains") is Lookup.ICONTAINS
