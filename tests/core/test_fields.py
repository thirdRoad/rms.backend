import pytest
from marshmallow import Schema, ValidationError, fields

from flaskr.core.base.fields import DelimitedList


class ListSchema(Schema):
    ids = DelimitedList(fields.Int())


class TestDelimitedList:
    def test_comma_separated_string_is_split(self):
        assert ListSchema().load({"ids": "1,2,3"}) == {"ids": [1, 2, 3]}

    def test_spaces_and_empty_items_are_removed(self):
        assert ListSchema().load({"ids": " 1 , ,2,"}) == {"ids": [1, 2]}

    def test_invalid_item_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            ListSchema().load({"ids": "1,abc"})

        assert exc_info.value.messages == {"ids": {1: ["Not a valid integer."]}}

    def test_empty_list_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            ListSchema().load({"ids": ","})

        assert exc_info.value.messages == {"ids": ["At least one value is required."]}
