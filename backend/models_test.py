from backend.config import Config
from backend.models import Recipe, Step, Replacement
from backend.functions import generate_new_id
from datetime import datetime
from pytest import raises


def step_creator(recipe: Recipe, steps_to_create=1, multiplier=1,
                 use_step_number_as_id=False) -> Recipe:
    """Helper function that adds steps to a provided recipe"""
    # Determine the next step number to create by finding the largest existing step number
    create_step_number = 1
    if recipe.steps:
        for step in recipe.steps:
            if step.number > create_step_number:
                create_step_number = step.number + 1

    steps_created = 0
    while steps_created < steps_to_create:
        if use_step_number_as_id:
            new_step = Step(step_id=create_step_number,
                            number=create_step_number,
                            text=f"step_{create_step_number}",
                            then_wait=(steps_created + 1) * multiplier,
                            note=f"step_{create_step_number} note")
        else:
            new_step = Step(number=create_step_number,
                            text=f"step_{create_step_number}",
                            then_wait=(steps_created + 1) * multiplier,
                            note=f"step_{create_step_number} note")
        recipe.steps.append(new_step)
        create_step_number += 1
        steps_created += 1

    return recipe


class TestStepModel:
    """Unit tests for the pynamodb-based Step model."""

    def test_step_attributes(self):
        """Foundational tests for a Step created without data"""
        step = Step()
        assert isinstance(step.step_id, str)
        assert step.number is None
        assert step.text is None
        assert step.then_wait == 0
        assert step.note is None

        # Add data one item at a time
        step.number = 7
        assert isinstance(step.step_id, str)
        assert step.number == 7
        assert step.text is None
        assert step.then_wait == 0
        assert step.note is None

        step.text = 'Another step test!!@'
        assert isinstance(step.step_id, str)
        assert step.number == 7
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 0
        assert step.note is None

        step.then_wait = 86856
        assert isinstance(step.step_id, str)
        assert step.number == 7
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 86856
        assert step.note is None

        step.note = 'Message in a bottle 0_o?'
        assert isinstance(step.step_id, str)
        assert step.number == 7
        assert step.text == 'Another step test!!@'
        assert step.then_wait == 86856
        assert step.note == 'Message in a bottle 0_o?'

    def test_step_constructor(self):
        step = Step(step_id='abc123',
                    number=3,
                    text='step test!',
                    then_wait=5573,
                    note='another note :D')

        assert step.step_id == 'abc123'
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

        step.text = '$#( switch it up $*&%'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&%'
        assert step.then_wait == 5573
        assert step.note == 'another note :D'

        step.then_wait = 415395
        assert step.number == 5
        assert step.text == '$#( switch it up $*&%'
        assert step.then_wait == 415395
        assert step.note == 'another note :D'

        step.note = 'something else :,X'
        assert step.number == 5
        assert step.text == '$#( switch it up $*&%'
        assert step.then_wait == 415395
        assert step.note == 'something else :,X'

        assert isinstance(step.__repr__(), str)

    def test_step_type_checks(self):
        step = Step(step_id='second StepId Test987',
                    number=3,
                    text='step test!',
                    then_wait=5573,
                    note='another note :D')

        assert isinstance(step.step_id, str)
        assert isinstance(step.number, int)
        assert isinstance(step.text, str)
        assert isinstance(step.then_wait, int)
        assert isinstance(step.note, str)

        step.step_id = None
        assert step.step_id is None

        step.number = None
        assert step.number is None

        step.text = None
        assert step.text is None

        step.then_wait = None
        assert step.then_wait is None
        # TODO: The Step model should probably update then_wait to 0 instead of None
        # https://stackoverflow.com/questions/6190468/how-to-trigger-function-on-value-change

        step.note = None
        assert step.note is None

    def test_step_to_dict(self):
        step = Step(step_id='third StepId Test003',
                    number=66,
                    text='another step test!',
                    then_wait=27,
                    note='yep, another note :D')

        assert isinstance(step.to_dict(), dict)
        assert step.to_dict() == {
            "step_id":   "third StepId Test003",
            "number":    66,
            "text":      "another step test!",
            "then_wait": 27,
            "note":      "yep, another note :D"
        }


class TestRecipeModel:
    """Unit tests for the pynamodb-based Recipe model."""
    test_recipe = Recipe()

    def test_recipe_meta_defaults(self):
        assert self.test_recipe.Meta.table_name == 'Recipe'
        assert self.test_recipe.Meta.region == Config.AWS_REGION

    def test_recipe_attribute_defaults(self):
        # Validate the model's default values
        assert isinstance(self.test_recipe.id, str)
        assert len(self.test_recipe.id) > 1
        assert self.test_recipe.name is None
        assert self.test_recipe.author is None
        assert self.test_recipe.source is None
        assert self.test_recipe.url is None

        assert self.test_recipe.difficulty == "Beginner"
        assert self.test_recipe.solve_for_start is True
        assert self.test_recipe.length == 0
        assert self.test_recipe.steps == []

        # Since no datetime values are provided, date_added, start_time, & last_modified
        #   should be generated immediately. Any difference between `now` and those
        #   values should be well under 1s
        now = datetime.utcnow()
        assert abs((now - self.test_recipe.date_added)).total_seconds() < 1
        assert abs((now - self.test_recipe.start_time)).total_seconds() < 1
        assert abs((now - self.test_recipe.last_modified)).total_seconds() < 1

    def test_recipe_attributes(self):
        self.test_recipe.id = "Cowabunga 123.4!"
        assert self.test_recipe.id == "Cowabunga 123.4!"

        self.test_recipe.name = "My 7th(!) favorite recipe."
        assert self.test_recipe.name == "My 7th(!) favorite recipe."

        self.test_recipe.author = "Voices in my head"
        assert self.test_recipe.author == "Voices in my head"

        long_string = "This is a very long string.  It has two sentences."
        self.test_recipe.source = long_string
        assert self.test_recipe.source == long_string

        invalid_url = "long-domain.com/food/chicken?fried=True&deliciousness_quotient=93"
        with raises(ValueError):
            assert self.test_recipe.url is None
            self.test_recipe.url = invalid_url

        url = "https://long-domain.com/food/chicken?fried=True&deliciousness_quotient=93"
        self.test_recipe.url = url
        assert self.test_recipe.url == url

        self.test_recipe.difficulty = "Iron Chef"
        assert self.test_recipe.difficulty == "Iron Chef"

        self.test_recipe.solve_for_start = False
        assert self.test_recipe.solve_for_start is False

        self.test_recipe.length = 23987
        assert self.test_recipe.length == 23987

        # Add steps to the recipe
        self.test_recipe.steps.append(Step(number=1, text="Preheat oven to 350°F."))
        assert len(self.test_recipe.steps) == 1
        assert isinstance(self.test_recipe.steps[0].step_id, str)
        assert self.test_recipe.steps[0].number == 1
        assert self.test_recipe.steps[0].text == "Preheat oven to 350°F."
        assert self.test_recipe.steps[0].then_wait == 0
        assert self.test_recipe.steps[0].note is None

        # Adding a step shouldn't update the recipe's length automatically
        assert self.test_recipe.length == 23987

        self.test_recipe.steps.append(Step(number=6, text="score the dough", then_wait=300))
        assert len(self.test_recipe.steps) == 2

        # Original step shouldn't change
        assert isinstance(self.test_recipe.steps[0].step_id, str)
        assert self.test_recipe.steps[0].number == 1
        assert self.test_recipe.steps[0].text == "Preheat oven to 350°F."
        assert self.test_recipe.steps[0].then_wait == 0
        assert self.test_recipe.steps[0].note is None

        # Validate the new step
        assert isinstance(self.test_recipe.steps[0].step_id, str)
        assert self.test_recipe.steps[1].number == 6
        assert self.test_recipe.steps[1].text == "score the dough"
        assert self.test_recipe.steps[1].then_wait == 300
        assert self.test_recipe.steps[1].note is None

        # Adding another step shouldn't update the recipe's length automatically
        assert self.test_recipe.length == 23987

        testing_date_added = datetime.utcnow()
        self.test_recipe.date_added = testing_date_added
        assert self.test_recipe.date_added == testing_date_added

        testing_start_time = datetime.utcnow()
        self.test_recipe.start_time = testing_start_time
        assert self.test_recipe.start_time == testing_start_time

        testing_last_modified = datetime.utcnow()
        self.test_recipe.last_modified = testing_last_modified
        assert self.test_recipe.last_modified == testing_last_modified

    def test_recipe_constructor(self):
        # Recipe with invalid URL and no steps
        now = datetime.utcnow()
        invalid_url = "some-domain.com/food?fried=True&quotient=61"
        valid_url = "http://some-domain.com/food?fried=True&quotient=61"
        with raises(ValueError):
            constructor_test = Recipe(id="10101",
                                      name="constructor_test",
                                      author="Abraham Lincoln",
                                      source="The hottest recipes of 1863",
                                      url=invalid_url,
                                      difficulty="Advanced",
                                      solve_for_start=False,
                                      length=53,
                                      date_added=now,
                                      start_time=now,
                                      last_modified=now,
                                      steps=[])

        # Recipe with valid URL and no steps
        constructor_test = Recipe(id="10102",
                                  name="constructor_test",
                                  author="Abraham Lincoln",
                                  source="The hottest recipes of 1863",
                                  url=valid_url,
                                  difficulty="Advanced",
                                  solve_for_start=False,
                                  length=53,
                                  date_added=now,
                                  start_time=now,
                                  last_modified=now,
                                  steps=[])

        assert isinstance(constructor_test.__repr__(), str)
        assert constructor_test.id == "10102"
        assert constructor_test.name == "constructor_test"
        assert constructor_test.author == "Abraham Lincoln"
        assert constructor_test.source == "The hottest recipes of 1863"
        assert constructor_test.url == "http://some-domain.com/food?fried=True&quotient=61"
        assert constructor_test.difficulty == "Advanced"
        assert constructor_test.solve_for_start is False
        assert constructor_test.length == 53
        assert constructor_test.date_added == now
        assert constructor_test.start_time == now
        assert constructor_test.last_modified == now
        assert constructor_test.steps == []

        # Create a new Recipe with 3 steps
        step_creator(constructor_test, steps_to_create=3, multiplier=100)
        recipe_with_steps = Recipe(id="10103",
                                   name="recipe_with_steps",
                                   author="Abraham Lincoln",
                                   source="The hottest recipes of 1863",
                                   url=valid_url,
                                   difficulty="Advanced",
                                   solve_for_start=False,
                                   length=53,
                                   date_added=now,
                                   start_time=now,
                                   last_modified=now,
                                   steps=constructor_test.steps)

        assert recipe_with_steps.id == "10103"
        assert recipe_with_steps.name == "recipe_with_steps"
        assert recipe_with_steps.author == "Abraham Lincoln"
        assert recipe_with_steps.source == "The hottest recipes of 1863"
        assert recipe_with_steps.url == "http://some-domain.com/food?fried=True&quotient=61"
        assert recipe_with_steps.difficulty == "Advanced"
        assert recipe_with_steps.solve_for_start is False
        assert recipe_with_steps.length == 53
        assert recipe_with_steps.date_added == now
        assert recipe_with_steps.start_time == now
        assert recipe_with_steps.last_modified == now
        assert recipe_with_steps.steps == constructor_test.steps

    def test_recipe_update_length(self):
        now = datetime.utcnow()
        length_test = Recipe(id="123456",
                             name="update_length_test",
                             difficulty="Intermediate",
                             steps=[])

        assert length_test.id == "123456"
        assert length_test.name == "update_length_test"
        assert length_test.author is None
        assert length_test.source is None
        assert length_test.url is None
        assert length_test.difficulty == "Intermediate"
        assert length_test.solve_for_start is True
        assert length_test.length == 0
        assert length_test.steps == []
        assert abs((now - length_test.date_added)).total_seconds() < 1
        assert abs((now - length_test.start_time)).total_seconds() < 1
        assert abs((now - length_test.last_modified)).total_seconds() < 1

        # Call update_length(), but don't write to the db
        prev_last_modified = length_test.last_modified
        length_test.update_length(save=False)

        # Nothing should change, including last_modified
        assert length_test.id == "123456"
        assert length_test.name == "update_length_test"
        assert length_test.author is None
        assert length_test.source is None
        assert length_test.url is None
        assert length_test.difficulty == "Intermediate"
        assert length_test.solve_for_start is True
        assert length_test.length == 0
        assert length_test.steps == []
        assert abs((now - length_test.date_added)).total_seconds() < 1
        assert abs((now - length_test.start_time)).total_seconds() < 1
        assert length_test.last_modified == prev_last_modified

        # Add 4 steps, update the length, and save to the db
        length_test = step_creator(length_test, steps_to_create=4, multiplier=100)
        length_test.update_length(save=True)

        # Step list, length, and last_modified should change
        assert length_test.id == "123456"
        assert length_test.name == "update_length_test"
        assert length_test.author is None
        assert length_test.source is None
        assert length_test.url is None
        assert length_test.difficulty == "Intermediate"
        assert length_test.solve_for_start is True
        assert length_test.length == 100 + 200 + 300 + 400
        assert len(length_test.steps) == 4
        assert abs((now - length_test.date_added)).total_seconds() < 1
        assert abs((now - length_test.start_time)).total_seconds() < 1
        assert length_test.last_modified > prev_last_modified

        # Add 2 more steps and update the length
        prev_last_modified = length_test.last_modified
        length_test = step_creator(length_test, steps_to_create=2, multiplier=100)
        length_test.update_length(save=True)

        # Only the step list & length should change
        assert length_test.id == "123456"
        assert length_test.name == "update_length_test"
        assert length_test.author is None
        assert length_test.source is None
        assert length_test.url is None
        assert length_test.difficulty == "Intermediate"
        assert length_test.solve_for_start is True
        assert length_test.length == 100 + 200 + 300 + 400 + 100 + 200
        assert len(length_test.steps) == 6
        assert abs((now - length_test.date_added)).total_seconds() < 1
        assert abs((now - length_test.start_time)).total_seconds() < 1
        assert length_test.last_modified > prev_last_modified

        # Remove all steps except the first one
        for step_index in range(len(length_test.steps)):
            length_test.steps.pop()
            if len(length_test.steps) == 1:
                break

        # Update length
        length_test.update_length(save=True)

        assert len(length_test.steps) == 1
        assert length_test.length == 100

    def test_recipe_update_last_modified(self):
        now = datetime.utcnow()
        original_date_added = datetime(year=2020, month=6, day=2,
                                       hour=17, minute=41, second=36)
        original_last_modified = datetime(year=2020, month=6, day=3,
                                          hour=21, minute=4, second=19)
        recipe = Recipe(id="123456",
                        name="routes_test",
                        difficulty="Beginner",
                        steps=[],
                        date_added=original_date_added,
                        last_modified=original_last_modified)

        # No changes yet
        assert recipe.date_added == original_date_added
        assert recipe.last_modified == original_last_modified

        # Call the update method
        recipe.update_last_modified()

        # Difference between `now` and `last_modified` should be well under 1s
        assert abs((now - recipe.last_modified)).total_seconds() < 1
        assert recipe.last_modified > original_last_modified

        # `date_added` should be the same
        assert recipe.date_added == original_date_added

    def test_to_dict(self):
        """Testing the .to_dict() method with both types of datetime outputs"""
        now = datetime.utcnow()

        # `dates_as_epoch` --> True
        dict_test1 = Recipe(id="112233",
                            name="dict_test1",
                            difficulty="Intermediate",
                            date_added=now,
                            start_time=now,
                            last_modified=now,
                            steps=[])

        assert isinstance(dict_test1.to_dict(), dict)
        assert dict_test1.to_dict(dates_as_epoch=True) == {
            "id":              "112233",
            "name":            "dict_test1",
            "author":          None,
            "source":          None,
            "url":             None,
            "difficulty":      "Intermediate",
            "solve_for_start": True,
            "length":          0,
            "date_added":      now.timestamp() * 1000,
            "start_time":      now.timestamp() * 1000,
            "last_modified":   now.timestamp() * 1000,
            "steps":           []
        }

        # `dates_as_epoch` --> False
        dict_test2 = Recipe(id="11223344",
                            author="James Beard",
                            name="dict_test2",
                            source="A prestigious cookbook",
                            url="https://www.seriouseats.com/",
                            difficulty="Intermediate",
                            solve_for_start=False,
                            length=350,
                            date_added=now,
                            start_time=now,
                            last_modified=now,
                            steps=[])

        # Default
        assert dict_test2.to_dict() == dict_test2.to_dict(dates_as_epoch=False)
        assert dict_test2.to_dict(dates_as_epoch=False) == {
            "id":              "11223344",
            "name":            "dict_test2",
            "author":          "James Beard",
            "source":          "A prestigious cookbook",
            "url":             "https://www.seriouseats.com/",
            "difficulty":      "Intermediate",
            "solve_for_start": False,
            "length":          350,
            "date_added":      now.isoformat(),
            "start_time":      now.isoformat(),
            "last_modified":   now.isoformat(),
            "steps":           []
        }

        # Validate that steps are properly converted
        dict_test3 = Recipe(id="1122334455",
                            name="dict_test3",
                            difficulty="Intermediate",
                            date_added=now,
                            start_time=now,
                            last_modified=now,
                            steps=[])

        step_creator(dict_test3, steps_to_create=2, multiplier=100,
                     use_step_number_as_id=True)

        steps_full = [
            {
                "step_id":   "1",
                "number":    1,
                "text":      "step_1",
                "then_wait": 100,
                "note":      "step_1 note"
            },
            {
                "step_id":   "2",
                "number":    2,
                "text":      "step_2",
                "then_wait": 200,
                "note":      "step_2 note"
            },
        ]

        assert dict_test3.to_dict(dates_as_epoch=True) == {
            "id":              "1122334455",
            "name":            "dict_test3",
            "author":          None,
            "source":          None,
            "url":             None,
            "difficulty":      "Intermediate",
            "solve_for_start": True,
            "length":          0,
            "date_added":      now.timestamp() * 1000,
            "start_time":      now.timestamp() * 1000,
            "last_modified":   now.timestamp() * 1000,
            "steps":           steps_full
        }


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
        assert isinstance(rep_full.__repr__(), str)
        assert isinstance(rep_full.scope, str)
        assert isinstance(rep_full.old, str)
        assert isinstance(rep_full.new, str)

    def test_to_dict(self):
        rep_full = Replacement(scope='ingredients', old='ounce', new='oz')

        assert rep_full.to_dict() == {
            "scope": "ingredients",
            "old":   "ounce",
            "new":   "oz"
        }
