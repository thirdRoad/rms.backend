from marshmallow import fields

from flaskr import create_app
from flaskr.core.base.routes import BaseRoutes
from flaskr.core.base.validators import BaseFilterValidator, BaseSortValidator


class SampleFilterValidator(BaseFilterValidator):
    name = fields.Str()


class SampleSortValidator(BaseSortValidator):
    SORT_FIELDS = {"name"}


class RouteWithValidators(BaseRoutes):
    filter_validator = SampleFilterValidator()
    sort_validator = SampleSortValidator()


class RouteWithoutValidators(BaseRoutes):
    pass


class TestBaseRoutesQueryParams:
    def setup_method(self):
        self.app = create_app("testing")

    def test_filters_and_sorting_are_read_from_query_params(self):
        with self.app.test_request_context("/?name=deniz&sort=-name"):
            route = RouteWithValidators()

            assert route.get_filters() == {"name__eq": "deniz"}
            assert route.get_sorting() == ["-name"]

    def test_params_are_ignored_without_validators(self):
        with self.app.test_request_context("/?name=deniz&sort=-name"):
            route = RouteWithoutValidators()

            assert route.get_filters() == {}
            assert route.get_sorting() == []
