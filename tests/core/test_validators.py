import pytest
from marshmallow import ValidationError, fields
from werkzeug.security import check_password_hash

from flaskr.core.base.validators import BaseValidator


class SampleValidator(BaseValidator):
    HASH_FIELDS = {"secret"}
    STRIP_FIELDS = {"title", "email"}
    LOWER_FIELDS = {"email", "code"}

    title = fields.Str(required=True)
    email = fields.Str(required=True)
    code = fields.Str(required=True)
    secret = fields.Str(required=True)


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
        assert check_password_hash(data["secret"], "s3cret")

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
