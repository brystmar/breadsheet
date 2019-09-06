import pytest
from app.models import Recipe, Step, Replacement
from app.functions import hms_to_string, seconds_to_hms
from datetime import date, datetime, timedelta
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class TestRecipeModel:
    """Test the pynamodb Recipe model."""
    test_recipe = Recipe()

    def test_recipe_meta_defaults(self):
        assert self.test_recipe.Meta.table_name == 'Recipe'
        assert self.test_recipe.Meta.region == 'us-west-2'

    def test_recipe_attribute_defaults(self):
        assert self.test_recipe.length is not None

    def test_recipe_attributes(self):
        self.test_recipe.id = "Cowabunga 123.4!"
        assert self.test_recipe.id == "Cowabunga 123.4!"

        self.test_recipe.name = "My 7th(!) favorite recipe."
        assert self.test_recipe.name == "My 7th(!) favorite recipe."

        self.test_recipe.author = "The voice in my head"
        assert self.test_recipe.author == "The voice in my head"

        self.test_recipe.source = "http://unnecessarilylongdomain.com/food/chicken?fried=True&deliciousness_quotient=9"
        assert self.test_recipe.source == "http://unnecessarilylongdomain.com/food/chicken?fried=True&deliciousness_quotient=9"

        self.test_recipe.difficulty = "Advanced"
        assert self.test_recipe.difficulty == "Advanced"

        self.test_recipe.length = 23987
        assert self.test_recipe.length == 23987
        # TODO: Validate that length == 0 when initialized.  Raises a TypeError that I can't wrap my head around.

        self.test_recipe.steps = []
        assert self.test_recipe.steps == []

        self.test_recipe.steps.append(Step(number=1, text="Preheat oven to 350°F."))
        assert len(self.test_recipe.steps) == 1
        assert self.test_recipe.steps[0].number == 1
        assert self.test_recipe.steps[0].text == "Preheat oven to 350°F."

        self.test_recipe.steps.append(Step(number=2, text="score the dough", then_wait=300))
        assert len(self.test_recipe.steps) == 2
        assert self.test_recipe.steps[0].number == 1
        assert self.test_recipe.steps[0].text == "Preheat oven to 350°F."
        assert self.test_recipe.steps[1].number == 2
        assert self.test_recipe.steps[1].text == "score the dough"
        assert self.test_recipe.steps[1].then_wait == 300

        assert self.test_recipe.date_added == date.today()


class TestReplacementModel:
    rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

    def test_replacement_meta_defaults(self):
        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == 'us-west-2'

    def test_replacement_null(self):
        rep_null = Replacement()

        rep_null.scope = 'directions'
        assert rep_null.scope == 'directions'

        rep_null.old = 'pounds'
        assert rep_null.old == 'pounds'

        assert rep_null.new == UnicodeAttribute
        rep_null.new = 'lbs'
        assert rep_null.new == 'lbs'

        # Ensure other values haven't changed
        assert rep_null.scope == 'directions'
        assert rep_null.old == 'pounds'

    def test_replacement_no_new(self):
        rep_no_new = Replacement(scope='ingredients', old='ounce')

        assert rep_no_new.scope == 'ingredients'
        assert rep_no_new.old == 'ounce'
        assert rep_no_new.new is None

        rep_no_new.new = 'lbs'
        assert rep_no_new.new == 'lbs'

        # Ensure other values haven't changed
        assert rep_no_new.scope == 'ingredients'
        assert rep_no_new.old == 'ounce'

    def test_replacement_defaults(self):
        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

        assert rep_full.scope == 'ingredients'
        assert rep_full.old == 'ounce'
        assert rep_full.new == 'oz'

    def test_replacement_all(self):
        pass
        # assert rep_full.scope in ('ingredients', 'directions')
        # assert rep_full.old is not None
        # assert rep_full.old != rep_full.new
