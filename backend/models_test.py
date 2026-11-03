"""Unit tests for the SQLAlchemy models. None of these touch the database."""
from backend.models import Recipe, RecipeStep, Replacement, parse_v1_datetime
from datetime import datetime, timezone
from pytest import raises
from uuid import UUID


def make_recipe(**kwargs) -> Recipe:
    data = {
        "name":       "Test Loaf",
        "date_added": 1550307600000,  # 2019-02-16T09:00:00Z, in JS ms
        "start_time": 1550311200000,
        "steps":      [{"number": 1, "text": "Mix", "then_wait": 1800, "note": "warm water"},
                       {"number": 2, "text": "Fold", "then_wait": 3600}]
    }
    data.update(kwargs)

    recipe = Recipe()
    recipe.update_from_v1(data)
    recipe.last_modified = recipe.date_added
    return recipe


class TestParseV1Datetime:
    fallback = datetime(2020, 1, 1, tzinfo=timezone.utc)

    def test_epoch_ms(self):
        assert parse_v1_datetime(1550307600000, self.fallback) == datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        assert parse_v1_datetime(1550307600000.5, self.fallback).microsecond == 500

    def test_empty_values_use_fallback(self):
        for value in (None, 0, "", "none", "Null", "NaN"):
            assert parse_v1_datetime(value, self.fallback) == self.fallback

    def test_iso_strings(self):
        assert parse_v1_datetime("2019-02-16T09:00:00+00:00", self.fallback) == \
               datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        assert parse_v1_datetime("2019-02-16T09:00:00", self.fallback).tzinfo == timezone.utc

    def test_invalid(self):
        with raises(ValueError):
            parse_v1_datetime("not a date", self.fallback)
        with raises(ValueError):
            parse_v1_datetime(True, self.fallback)


class TestRecipeModel:
    def test_update_from_v1(self):
        recipe = make_recipe(author="A. Baker", difficulty="Advanced", solve_for_start=False)

        assert isinstance(recipe.id, UUID)
        assert recipe.id.version == 7
        assert recipe.name == "Test Loaf"
        assert recipe.author == "A. Baker"
        assert recipe.source is None
        assert recipe.difficulty == "Advanced"
        assert recipe.solve_for_start is False
        assert recipe.date_added == datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        assert recipe.start_time == datetime(2019, 2, 16, 10, tzinfo=timezone.utc)
        assert [s.position for s in recipe.steps] == [1, 2]
        assert [(s.wait_min, s.wait_max) for s in recipe.steps] == [(1800, 1800), (3600, 3600)]

    def test_defaults(self):
        recipe = Recipe()
        recipe.update_from_v1({"name": "Bare"})

        assert recipe.difficulty == "Beginner"
        assert recipe.solve_for_start is True
        assert recipe.steps == []
        assert recipe.length == 0
        assert abs((datetime.now(timezone.utc) - recipe.date_added).total_seconds()) < 1

    def test_start_time_falls_back_to_date_added_when_null(self):
        recipe = make_recipe(start_time=None)
        assert recipe.start_time == recipe.date_added

    def test_name_required(self):
        with raises(KeyError):
            Recipe().update_from_v1({"author": "nobody"})

    def test_length_is_computed(self):
        recipe = make_recipe()
        assert recipe.length == 5400

        recipe.set_steps_from_v1([{"text": "Bake", "then_wait": 2700}])
        assert recipe.length == 2700

    def test_steps_keep_ids_when_matched(self):
        recipe = make_recipe()
        first, second = recipe.steps

        # Reorder, drop nothing, and add one new step
        recipe.set_steps_from_v1([
            {"step_id": str(second.id), "number": 2, "text": "Fold", "then_wait": 60},
            {"step_id": str(first.id), "number": 1, "text": "Mix", "then_wait": 30},
            {"step_id": "an-id-the-ui-made-up", "number": 3, "text": "Bake", "then_wait": 0}
        ])

        assert recipe.steps[0] is second
        assert recipe.steps[1] is first
        assert recipe.steps[2] not in (first, second)
        assert [s.position for s in recipe.steps] == [1, 2, 3]

    def test_to_dict_epoch(self):
        recipe = make_recipe(url="https://example.com")
        output = recipe.to_dict(dates_as_epoch=True)

        assert output == {
            "id":              str(recipe.id),
            "name":            "Test Loaf",
            "author":          None,
            "source":          None,
            "url":             "https://example.com",
            "difficulty":      "Beginner",
            "solve_for_start": True,
            "length":          5400,
            "date_added":      1550307600000.0,
            "start_time":      1550311200000.0,
            "last_modified":   1550307600000.0,
            "steps":           [
                {"step_id": str(recipe.steps[0].id), "number": 1, "text": "Mix", "then_wait": 1800,
                 "note": "warm water"},
                {"step_id": str(recipe.steps[1].id), "number": 2, "text": "Fold", "then_wait": 3600,
                 "note": None}
            ]
        }
        assert list(output) == ["id", "name", "author", "source", "url", "difficulty", "solve_for_start",
                                "length", "date_added", "start_time", "last_modified", "steps"]

    def test_to_dict_iso(self):
        output = make_recipe(author="").to_dict()

        assert output["author"] is None
        assert output["date_added"] == "2019-02-16T09:00:00+00:00"
        assert output["start_time"] == "2019-02-16T10:00:00+00:00"
        assert output["last_modified"] == "2019-02-16T09:00:00+00:00"

    def test_repr(self):
        recipe = make_recipe()
        assert repr(recipe) == f"<Recipe | id: {recipe.id}, name: Test Loaf, length: 5400, steps: 2>"
        assert repr(recipe.steps[0]) == f"<Step #1, id: {recipe.steps[0].id}, then_wait: 1800>"


class TestRecipeStepModel:
    def test_to_dict_empty_note(self):
        step = RecipeStep(position=3, text="Shape", note="", wait_min=0, wait_max=0)
        assert step.to_dict()["note"] is None
        assert step.to_dict()["number"] == 3


class TestReplacementModel:
    def test_to_dict(self):
        rep = Replacement(scope='ingredients', old='ounce', new='oz')

        assert rep.to_dict() == {
            "scope": "ingredients",
            "old":   "ounce",
            "new":   "oz"
        }

    def test_repr(self):
        rep = Replacement(scope='ingredients', old='ounce', new='oz')
        assert repr(rep) == "<Replacement Text | scope: ingredients, old: ounce, new: oz>"
