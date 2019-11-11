import pytest
from config import Config
from backend.models import Recipe, Step, Replacement
from backend.recipe_routes import generate_new_id
from datetime import datetime, timedelta


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
        new_step = Step(number=step_number, text=f"step_{step_number}",
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

        step.when = 'build me a string;!^'
        assert step.number == 2
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 86856
        assert step.note == 'Message in a bottle 0_o?'

    def test_step_constructor(self):
        step = Step(number=3, text='step test!', then_wait=5573, note='another note :D', when='sometime...?')

        assert step.number == 3
        assert step.text == 'step test!'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'
        assert step.when == 'at some point in time :O'

        # Update values one at a time
        step.number = 5
        assert step.number == 5
        assert step.text == 'step test!'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'
        assert step.when == 'at some point in time :O'

        step.text = '$#( switch it up $*&'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'
        assert step.when == 'at some point in time :O'

        step.then_wait = 415395
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 415395
        assert step.note == 'another note :D'
        assert step.when == 'at some point in time :O'

        step.note = 'something else :,X'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 415395
        assert step.note == 'something else :,X'
        assert step.when == 'at some point in time :O'

        step.when = 'maybe in the future?'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&'
        assert step.then_wait == 415395
        assert step.note == 'something else :,X'
        assert step.when == 'maybe in the future?'

    def test_step_type_checks(self):
        step = Step()
        pass


class TestRecipeModel:
    """Unit tests for the pynamodb-based Recipe model."""
    test_recipe = Recipe()

    def test_recipe_meta_defaults(self):
        assert self.test_recipe.Meta.table_name == 'Recipe'
        assert self.test_recipe.Meta.region == Config.aws_region

    def test_recipe_attribute_defaults(self):
        pass
        # TODO: Validate length == 0 when initialized.  Raises a TypeError that I can't wrap my head around.
        #  self = length = {'N': '0'}
        #  def __bool__(self):
        #   Prevent users from accidentally comparing the condition object instead of the attribute instance
        #   raise TypeError("unsupported operand type(s) for bool: {}".format(self.__class__.__name__))
        #   TypeError: unsupported operand type(s) for bool: Comparison
        #
        # TODO: Validate length >= 0

    def test_recipe_attributes(self):
        self.test_recipe.id = "Cowabunga 123.4!"
        assert self.test_recipe.id == "Cowabunga 123.4!"

        self.test_recipe.name = "My 7th(!) favorite recipe."
        assert self.test_recipe.name == "My 7th(!) favorite recipe."

        self.test_recipe.author = "The voice in my head"
        assert self.test_recipe.author == "The voice in my head"

        self.test_recipe.source = "http://longdomain.com/food/chicken?fried=True&deliciousness_quotient=9"
        assert self.test_recipe.source == "http://longdomain.com/food/chicken?fried=True&deliciousness_quotient=9"

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

        # TODO: Validate date_added == datetime.utcnow() when initialized.  Raises an AttributeError:
        #  self = <pynamodb.attributes.UTCDateTimeAttribute object at 0x103a8c588>
        #  value = datetime(2019, 9, 11)

    def test_recipe_adjust_start_time(self):
        start_time = datetime(2019, 9, 14, 10, 0, 0)
        recipe = Recipe(id=f"test_{generate_new_id()}", length=0, start_time=start_time)
        assert recipe.start_time == start_time

        # Start 35 minutes later
        recipe.adjust_start_time(seconds=35 * 60)
        assert recipe.start_time == datetime(2019, 9, 14, 10, 35, 0)

        # Start 3 hrs, 10 min sooner
        recipe.adjust_start_time(seconds=-1 * (10800 + 600))
        assert recipe.start_time == datetime(2019, 9, 14, 7, 25, 0)

    def test_recipe_update_length(self):
        recipe = Recipe(id=f"test_{generate_new_id()}", length=0, steps=[])
        # with pytest.raises(TypeError):
        #     pass
        assert recipe.length == 0
        recipe.update_length(save=False)
        assert recipe.length == 0

        # Add 4 steps
        recipe = step_creator(recipe, 4, 100)
        recipe.update_length(save=False)
        assert recipe.length == 100 + 200 + 300 + 400


class TestReplacementModel:
    """Unit tests for the pynamodb-based Replacement model."""
    rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

    def test_replacement_meta_defaults(self):
        rep_full = Replacement()
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.aws_region

        rep_full = Replacement(scope='ingredients')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.aws_region

        rep_full = Replacement(scope='ingredients', old='ounce')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.aws_region

        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')
        assert rep_full.Meta.table_name == 'Replacement'
        assert rep_full.Meta.region == Config.aws_region

    def test_replacement_null(self):
        rep_null = Replacement()

        rep_null.scope = 'directions'
        assert rep_null.scope == 'directions'

        rep_null.old = 'pounds'
        assert rep_null.scope == 'directions'
        assert rep_null.old == 'pounds'

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
        pass
        # with pytest.raises(TypeError):
        #     rep = Replacement(scope=object)
        #
        # with pytest.raises(TypeError):
        #     rep = Replacement(scope='test', old=object)
        #
        # with pytest.raises(TypeError):
        #     rep = Replacement(scope='test', old='old_test', new=object)
