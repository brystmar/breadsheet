import pytest
from app.models import Recipe, Step, Replacement
from app.functions import hms_to_string, seconds_to_hms
from datetime import date, datetime, timedelta
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class TestRecipeModel(Recipe):
    """Test the pynamodb Recipe model."""
    def setup(self):
        assert self.length == 0

    def test_meta_defaults(self):
        assert self.Meta.table_name == 'Recipe'
        assert self.Meta.region == 'us-west-2'

    def test_attributes(self):
        self.id = "Cowabunga 123.4!"
        assert self.id == "Cowabunga 123.4!"
