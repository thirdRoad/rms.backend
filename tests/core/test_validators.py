from enum import Enum

import pytest
from marshmallow import ValidationError, fields
from werkzeug.datastructures import MultiDict

from flaskr.core.base.fields import DelimitedList
from flaskr.core.base.filters import Lookup
from flaskr.core.base.validators import (
    BaseFilterValidator,
    BaseSortValidator,
    BaseValidator,
    FieldOption,
)
from flaskr.core.security import verify_password


class SampleValidator(BaseValidator):
    title = fields.Str(required=True, metadata={FieldOption.STRIP: True})
    email = fields.Str(
        required=True, metadata={FieldOption.STRIP: True, FieldOption.LOWER: True}
    )
    code = fields.Str(required=True, metadata={FieldOption.LOWER: True})
    secret = fields.Str(required=True, metadata={FieldOption.HASH: True})


class SamplePartialValidator(SampleValidator):
    PARTIAL_FIELDS = {"title", "code", "secret"}  # email stays required


VALID = {"title": "Title", "email": "a@b.com", "code": "abc", "secret": "s3cret"}


class TestBaseValidator:
    def test_strip_fields_only_trims(self):
        data = SampleValidator().validate_data({**VALID, "title": "  My Title  "})

        assert data["title"] == "My Title"

    def test_lower_fields_only_lowercases(self):
        data = SampleValidator().validate_data({**VALID, "code": "  ABC  "})

        assert data["code"] == "  abc  "

    def test_strip_and_lower_fields_combined(self):
        data = SampleValidator().validate_data({**VALID, "email": "  A@B.COM "})

        assert data["email"] == "a@b.com"

    def test_hash_fields_are_hashed(self):
        data = SampleValidator().validate_data(VALID)

        assert data["secret"] != "s3cret"
        assert verify_password(data["secret"], "s3cret")

    def test_partial_fields_are_optional(self):
        data = SamplePartialValidator().validate_data({"email": "a@b.com"})

        assert data == {"email": "a@b.com"}

    def test_fields_outside_partial_stay_required(self):
        with pytest.raises(ValidationError) as exc_info:
            SamplePartialValidator().validate_data({"title": "Title"})

        assert exc_info.value.messages == {
            "email": ["Missing data for required field."]
        }

    def test_without_partial_fields_all_required_fields_are_enforced(self):
        with pytest.raises(ValidationError) as exc_info:
            SampleValidator().validate_data({})

        assert set(exc_info.value.messages) == {"title", "email", "code", "secret"}

    @pytest.mark.parametrize("payload", [None, [], "text", 123])
    def test_non_dict_input_raises_validation_error(self, payload):
        with pytest.raises(ValidationError) as exc_info:
            SampleValidator().validate_data(payload)

        assert exc_info.value.messages == {"_schema": ["Invalid input type."]}

    def test_non_string_values_raise_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            SampleValidator().validate_data({**VALID, "email": 1, "title": ["x"]})

        assert exc_info.value.messages == {
            "email": ["Not a valid string."],
            "title": ["Not a valid string."],
        }


class SampleStatus(Enum):
    PREPARATION = "preparation"
    DONE = "done"


class SampleFilterValidator(BaseFilterValidator):
    name = fields.Str(metadata={FieldOption.STRIP: True, FieldOption.LOWER: True})
    statuses = DelimitedList(
        fields.Enum(SampleStatus, by_value=True),
        metadata={
            FieldOption.STRIP: True,
            FieldOption.LOWER: True,
            FieldOption.COLUMN: "status",
            FieldOption.LOOKUP: Lookup.IN,
        },
    )
    title = fields.Str(metadata={FieldOption.LOOKUP: Lookup.ICONTAINS})
    category = fields.Int(metadata={FieldOption.COLUMN: "category_id"})
    created_after = fields.Str(
        metadata={FieldOption.COLUMN: "created_at", FieldOption.LOOKUP: Lookup.GTE}
    )


class TestBaseFilterValidator:
    def validate(self, **params: str) -> dict:
        return SampleFilterValidator().validate_query(MultiDict(params))

    def test_lookup_defaults_to_eq(self):
        assert self.validate(name="deniz") == {"name__eq": "deniz"}

    def test_lookup_option_sets_operator(self):
        assert self.validate(title="den") == {"title__icontains": "den"}

    def test_column_option_sets_target_column(self):
        assert self.validate(category="5") == {"category_id__eq": 5}

    def test_column_and_lookup_options_combined(self):
        assert self.validate(created_after="2026-11-01") == {
            "created_at__gte": "2026-11-01"
        }

    def test_strip_and_lower_options_are_applied(self):
        assert self.validate(name="  DeNiZ ") == {"name__eq": "deniz"}

    def test_empty_and_blank_params_are_dropped(self):
        assert self.validate(name="", title="   ") == {}

    def test_unknown_params_are_ignored(self):
        assert self.validate(name="deniz", page="2", foo="bar") == {"name__eq": "deniz"}

    def test_invalid_type_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            self.validate(category="abc")

        assert exc_info.value.messages == {"category": ["Not a valid integer."]}

    def test_delimited_enum_list_with_in_lookup(self):
        assert self.validate(statuses=" Done, PREPARATION ") == {
            "status__in": [SampleStatus.DONE, SampleStatus.PREPARATION]
        }

    def test_delimited_list_invalid_item_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            self.validate(statuses="done,unknown")

        assert set(exc_info.value.messages["statuses"]) == {1}


class SampleSortValidator(BaseSortValidator):
    SORT_FIELDS = {"name", "created_at"}


class TestBaseSortValidator:
    def validate(self, **params: str) -> dict:
        return SampleSortValidator().validate_query(MultiDict(params))

    def test_sort_is_split_into_list(self):
        assert self.validate(sort="-created_at,name") == {
            "sort": ["-created_at", "name"]
        }

    def test_missing_sort_returns_empty_list(self):
        assert self.validate() == {"sort": []}

    def test_spaces_and_empty_items_are_removed(self):
        assert self.validate(sort=" name , ,-created_at,") == {
            "sort": ["name", "-created_at"]
        }

    def test_unknown_params_are_ignored(self):
        assert self.validate(sort="name", name="deniz") == {"sort": ["name"]}

    def test_field_outside_sort_fields_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            self.validate(sort="name,-password")

        assert exc_info.value.messages == {
            "sort": ["Invalid sort field(s): -password. Allowed: created_at, name."]
        }
