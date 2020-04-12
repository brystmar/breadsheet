from backend.models import Recipe, Step
from backend.recipe_routes import RecipeApi, RecipeCollectionApi
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
from flask_restful import reqparse
import json


class TestRecipeCollectionApi:
    def test_get(self):
        # TODO: Write unit tests for recipe routes
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
    def test_parse_timestamp(self):
        dt_check = datetime(year=2019,
                            month=11,
                            day=11,
                            hour=2,
                            minute=15,
                            second=0,
                            tzinfo=timezone.utc)
