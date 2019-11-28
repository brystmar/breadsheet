from backend.models import Recipe, Step
from backend.recipe_routes import RecipeApi, RecipeCollectionApi, parse_recipe_args, parse_timestamp
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
from flask_restful import reqparse
import json


class TestRecipeCollectionApi:
    def test_get(self):
        pass

    def test_post(self):
        pass


class TestRecipeApi:
    def test_get(self):
        pass

    def test_put(self):
        pass

    def test_delete(self):
        pass


class TestRecipeFunctions:
    def test_parse_recipe_args(self):
        test_parser = reqparse.RequestParser()

    def test_parse_timestamp(self):
        assert parse_timestamp(None) is None

        dt_check = datetime(year=2019,
                            month=11,
                            day=11,
                            hour=2,
                            minute=15,
                            second=0,
                            tzinfo=timezone.utc)

        assert parse_timestamp('2019-11-11 02:15:00+00:00') == dt_check
        assert parse_timestamp('2019-11-11 02:15:00-00:00') == dt_check
