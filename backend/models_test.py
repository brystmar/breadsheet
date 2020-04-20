from backend.config import Config
from backend.models import Recipe, Step, Replacement
from backend.functions import generate_new_id
from datetime import datetime
import pytest


def step_creator(recipe_input: Recipe, steps_to_create, multiplier=1) -> Recipe:
    # Determine the next step number to use
    step_number = 1
    if recipe_input.steps:
        for step in recipe_input.steps:
            if step.number > step_number:
                step_number = step.number
    else:
        step_number = 1

    while step_number <= steps_to_create:
        new_step = Step(number=step_number,
                        text=f"step_{step_number}",
                        then_wait=step_number * multiplier)
        recipe_input.steps.append(new_step)
        step_number += 1

    return recipe_input


class TestStepModel:
    """Unit tests for the pynamodb-based Step model."""
    def test_step_attributes(self):
        step = Step()

        step.number = 2
        assert step.number == 2

        step.text = 'Another step test!!@'
        assert step.number == 2
        assert step.text == 'Another step test!!@'

        step.then_wait = 86856
        assert step.number == 2
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 86856

        step.note = 'Message in a bottle 0_o?'
        assert step.number == 2
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 86856
        assert step.note == 'Message in a bottle 0_o?'

    def test_step_constructor(self):
        step = Step(number=3,
                    text='step test!',
                    then_wait=5573,
                    note='another note :D')

        assert len(step.step_id) > 1
        assert step.number == 3
        assert step.text == 'step test!'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'

        # Update values one at a time
        step.number = 5
        assert step.number == 5
        assert step.text == 'step test!'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'

        step.text = '$#( switch it up $*&'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'

        step.then_wait = 415395
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 415395
        assert step.note == 'another note :D'

        step.note = 'something else :,X'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 415395
        assert step.note == 'something else :,X'

    def test_step_type_checks(self):
        step = Step(number=3,
                    text='step test!',
                    then_wait=5573,
                    note='another note :D')

        assert isinstance(step.step_id, str)
        assert isinstance(step.number, int)
        assert isinstance(step.text, str)
        assert isinstance(step.then_wait, int)
        assert isinstance(step.note, str)

        step.text = None
        assert step.text is None

        step.then_wait = None
        assert step.then_wait is None
        # TODO: My class really should update then_wait to 0 instead of None
        # https://stackoverflow.com/questions/6190468/how-to-trigger-function-on-value-change


class TestRecipeModel:
    """Unit tests for the pynamodb-based Recipe model."""
    test_recipe = Recipe()

    def test_recipe_meta_defaults(self):
        assert self.test_recipe.Meta.table_name == 'Recipe'
        assert self.test_recipe.Meta.region == Config.AWS_REGION

    def test_recipe_attribute_defaults(self):
        # Validate that the default values were applied
        assert self.test_recipe.length == 0
        assert self.test_recipe.difficulty == "Beginner"
        assert self.test_recipe.solve_for_start is True

        # Since neither value was provided, date_added & start_time should be generated immediately
        #  Difference between `now` and those values should be well under 1s
        now = datetime.utcnow()
        assert (now - self.test_recipe.date_added).total_seconds() < 1
        assert (now - self.test_recipe.start_time).total_seconds() < 1

    def test_recipe_attributes(self):
        self.test_recipe.id = "Cowabunga 123.4!"
        assert self.test_recipe.id == "Cowabunga 123.4!"

        self.test_recipe.name = "My 7th(!) favorite recipe."
        assert self.test_recipe.name == "My 7th(!) favorite recipe."

        self.test_recipe.author = "The voice in my head"
        assert self.test_recipe.author == "The voice in my head"

        long_string = "http://longdomain.com/food/chicken?fried=True&deliciousness_quotient=9"
        self.test_recipe.source = long_string
        assert self.test_recipe.source == long_string

        self.test_recipe.difficulty = "Advanced"
        assert self.test_recipe.difficulty == "Advanced"

        self.test_recipe.length = 23987
        assert self.test_recipe.length == 23987

        # Add steps to the recipe
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

        testing_date_added = datetime.utcnow()
        self.test_recipe.date_added = testing_date_added
        assert self.test_recipe.date_added == testing_date_added

        testing_start_time = datetime.utcnow()
        self.test_recipe.start_time = testing_start_time
        assert self.test_recipe.start_time == testing_start_time

        testing_finish_time = datetime.utcnow()
        self.test_recipe.finish_time = testing_finish_time
        assert self.test_recipe.finish_time == testing_finish_time

    def test_recipe_update_length(self):
        recipe = Recipe(id="123456",
                        name="routes_test",
                        difficulty="Easy",
                        steps=[])

        assert recipe.length == 0
        recipe.update_length(save=False)
        assert recipe.length == 0

        # Add 4 steps
        recipe = step_creator(recipe, 4, 100)
        recipe.update_length(save=False)
        assert recipe.length == 100 + 200 + 300 + 400


class TestReplacementModel:
    """Unit tests for the pynamodb-based Replacement model."""
    def test_replacement_meta_defaults(self):
        rep_full = Replacement()
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.AWS_REGION

        rep_full = Replacement(scope='ingredients')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.AWS_REGION

        rep_full = Replacement(scope='ingredients', old='ounce')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.AWS_REGION

        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.AWS_REGION

    def test_replacement_null(self):
        rep_null = Replacement()

        assert rep_null.scope is None
        rep_null.scope = 'directions'
        assert rep_null.scope == 'directions'

        assert rep_null.old is None
        rep_null.old = 'pounds'
        assert rep_null.scope == 'directions'
        assert rep_null.old == 'pounds'

        assert rep_null.new is None
        rep_null.new = 'lbs'
        assert rep_null.scope == 'directions'
        assert rep_null.old == 'pounds'
        assert rep_null.new == 'lbs'

    def test_replacement_constructor(self):
        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

        assert rep_full.scope == 'ingredients'
        assert rep_full.old == 'ounce'
        assert rep_full.new == 'oz'

    def test_replacement_type_checks(self):
        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

        assert isinstance(rep_full, Replacement)
        assert isinstance(rep_full.scope, str)
        assert isinstance(rep_full.old, str)
        assert isinstance(rep_full.new, str)
