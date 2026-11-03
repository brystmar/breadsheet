"""Unit tests for the DynamoDB migration's transforms. None of these touch DynamoDB or Postgres."""
from datetime import datetime, timezone
from decimal import Decimal
from etc.migrate_dynamodb import MigrationError, comparable_recipes, parse_dynamodb_datetime, plain, \
    to_recipe, to_replacement, uuid7_at
from pytest import raises

# Shaped like a production item after plain(): ISO strings, ints, every step with a note
ITEM = {
    "id":              "1560122081.000008",
    "name":            "Country Sourdough: Pain de Campagne",
    "author":          "Chad Robertson",
    "source":          "Tartine Bread",
    "difficulty":      "Iron Chef",
    "solve_for_start": False,
    "length":          5400,
    "date_added":      "2019-02-16T09:00:00.000000+0000",
    "start_time":      "2019-02-16T10:30:00.500000+0000",
    "last_modified":   "2026-11-03T18:00:00.000000+0000",
    "steps":           [{"step_id": "a", "number": 1, "text": "Mix", "then_wait": 1800, "note": "warm water"},
                        {"step_id": "b", "number": 2, "text": "Fold", "then_wait": 3600, "note": ""}]
}


class TestUuid7At:
    def test_timestamp_and_version(self):
        moment = datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        new_id = uuid7_at(moment)

        assert new_id.version == 7
        assert new_id.variant == "specified in RFC 4122"
        assert new_id.int >> 80 == int(moment.timestamp() * 1000)

    def test_offset_orders_ids(self):
        moment = datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        ids = [uuid7_at(moment, offset_ms=n) for n in range(5)]
        assert ids == sorted(ids)
        assert len(set(ids)) == 5

    def test_random(self):
        moment = datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        assert uuid7_at(moment) != uuid7_at(moment)


class TestHelpers:
    def test_parse_dynamodb_datetime(self):
        assert parse_dynamodb_datetime("2020-09-20T17:57:01.855970+0000") == \
               datetime(2020, 9, 20, 17, 57, 1, 855970, tzinfo=timezone.utc)

    def test_plain(self):
        assert plain({"a": Decimal("1800"), "b": [Decimal("1.5"), "x"], "c": True}) == \
               {"a": 1800, "b": [1.5, "x"], "c": True}
        assert isinstance(plain(Decimal("1800")), int)

    def test_comparable_recipes(self):
        recipe = {"id": "x", "name": "n", "last_modified": 1.0,
                  "steps": [{"step_id": "s", "number": 1, "text": "t"}]}
        assert comparable_recipes([recipe]) == [{"name": "n", "steps": [{"number": 1, "text": "t"}]}]


class TestToRecipe:
    def test_fields(self):
        recipe = to_recipe(ITEM)

        assert recipe.name == "Country Sourdough: Pain de Campagne"
        assert recipe.author == "Chad Robertson"
        assert recipe.url is None
        assert recipe.difficulty == "Iron Chef"
        assert recipe.solve_for_start is False
        assert recipe.date_added == datetime(2019, 2, 16, 9, tzinfo=timezone.utc)
        assert recipe.start_time == datetime(2019, 2, 16, 10, 30, 0, 500000, tzinfo=timezone.utc)
        assert recipe.last_modified == datetime(2026, 11, 3, 18, tzinfo=timezone.utc)
        assert recipe.length == 5400

    def test_ids_dated_to_date_added(self):
        recipe = to_recipe(ITEM)
        date_added_ms = int(recipe.date_added.timestamp() * 1000)

        assert recipe.id.int >> 80 == date_added_ms
        assert [s.id.int >> 80 for s in recipe.steps] == [date_added_ms + 1, date_added_ms + 2]

    def test_steps(self):
        steps = to_recipe(ITEM).steps

        assert [(s.position, s.text, s.wait_min, s.wait_max) for s in steps] == \
               [(1, "Mix", 1800, 1800), (2, "Fold", 3600, 3600)]
        assert steps[0].note == "warm water"
        assert steps[1].note is None

    def test_missing_last_modified_uses_date_added(self):
        item = {k: v for k, v in ITEM.items() if k != 'last_modified'}
        recipe = to_recipe(item)
        assert recipe.last_modified == recipe.date_added

    def test_blank_optional_fields(self):
        recipe = to_recipe({**ITEM, "author": "", "source": None, "url": ""})
        assert (recipe.author, recipe.source, recipe.url) == (None, None, None)

    def test_number_mismatch_stops(self):
        steps = [{**ITEM['steps'][0], "number": 2}, {**ITEM['steps'][1], "number": 1}]
        with raises(MigrationError, match="position 1 has number 2"):
            to_recipe({**ITEM, "steps": steps})

    def test_invalid_wait_stops(self):
        for then_wait in (-60, 1.5):
            steps = [{**ITEM['steps'][0], "then_wait": then_wait}]
            with raises(MigrationError, match="invalid then_wait"):
                to_recipe({**ITEM, "steps": steps})

    def test_no_steps(self):
        recipe = to_recipe({**ITEM, "steps": []})
        assert recipe.steps == []
        assert recipe.length == 0


class TestToReplacement:
    def test_whitespace_preserved(self):
        rep = to_replacement({"scope": "directions", "old": "°F", "new": " degrees F "})
        assert (rep.scope, rep.old, rep.new) == ("directions", "°F", " degrees F ")
