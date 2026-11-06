"""Tests for recipe detail levels, the Then Wait, and drafts (breadsheet#30)."""
from backend.database import db
from backend.models import Recipe, RecipeStep, utc_now
from backend.recipe_routes_v2_test import RECIPE, create, make_default, register
from pytest import fixture, mark, raises
from uuid import UUID
from sqlalchemy.exc import IntegrityError

HOUR = 3600


@fixture
def baker(client):
    register(client, 'baker')
    return client


@fixture
def other(app, client):
    browser = app.test_client()
    register(browser, 'other')
    return browser


def with_steps(*steps, **fields):
    return {**RECIPE, **fields, "steps": list(steps)}


def step_of(client, *steps, **fields):
    response = create(client, with_steps(*steps, **fields))
    assert response.status_code == 201, response.json
    return response.json['recipe']['steps'][0]


class TestDefaultWait:
    """Pure rules, no database: where a bake starts each step."""

    @mark.parametrize('then_wait, wait_min, wait_max, expected', [
        (7 * HOUR, 6 * HOUR, 8 * HOUR, 7 * HOUR),   # the Then Wait wins
        (0, 12 * HOUR, 24 * HOUR, 0),               # even outside its range ("or skip if your starter is active")
        (None, 2 * HOUR, 4 * HOUR, 3 * HOUR),       # a range alone: the middle
        (None, 60, 150, 120),                       # the middle (105s) rounded to the nearest minute
        (None, 90, 90, 90),                         # a zero-width range is never rounded
        (None, 60, 89, 60),                         # rounding stays inside the range
    ])
    def test_default_wait(self, then_wait, wait_min, wait_max, expected):
        step = RecipeStep(then_wait=then_wait, wait_min=wait_min, wait_max=wait_max)
        assert step.default_wait == expected

    def test_unknown_hands_on_is_not_zero(self):
        assert RecipeStep(active_seconds=None, needs_presence=None).hands_on() == (600, True, True)
        assert RecipeStep(active_seconds=0, needs_presence=False).hands_on() == (0, False, False)
        assert RecipeStep(active_seconds=900, needs_presence=True).hands_on() == (900, False, True)


class TestThenWait:
    def test_a_then_wait_alone_is_simple(self, baker):
        step = step_of(baker, {"text": "Mix", "then_wait": 1800})
        assert (step['then_wait'], step['wait_min'], step['wait_max'], step['default_wait']) == (1800, 1800, 1800, 1800)

    def test_a_range_around_the_then_wait(self, baker):
        step = step_of(baker, {"text": "Feed", "then_wait": 7 * HOUR, "wait_min": 6 * HOUR, "wait_max": 8 * HOUR})
        assert (step['then_wait'], step['default_wait'], step['warnings']) == (7 * HOUR, 7 * HOUR, [])

    def test_a_range_without_a_then_wait_starts_in_the_middle(self, baker):
        step = step_of(baker, {"text": "Proof", "wait_min": 2 * HOUR, "wait_max": 4 * HOUR})
        assert step['then_wait'] is None
        assert step['default_wait'] == 3 * HOUR

    def test_a_then_wait_outside_its_range_is_saved_and_flagged(self, baker):
        step = step_of(baker, {"text": "Revive levain", "then_wait": 0, "wait_min": 12 * HOUR, "wait_max": 24 * HOUR})
        assert step['then_wait'] == 0
        assert step['warnings'] == ['then_wait_outside_range']

    def test_no_wait_at_all_is_zero(self, baker):
        step = step_of(baker, {"text": "Bake"})
        assert (step['then_wait'], step['wait_min'], step['wait_max']) == (0, 0, 0)

    def test_length_follows_the_default_waits(self, baker):
        recipe = create(baker, with_steps({"text": "Feed", "then_wait": 7 * HOUR, "wait_min": 6 * HOUR, "wait_max": 8 * HOUR},
                                          {"text": "Proof", "wait_min": 2 * HOUR, "wait_max": 4 * HOUR})).json['recipe']
        assert recipe['length_seconds'] == 10 * HOUR
        assert recipe['length_max_seconds'] == 12 * HOUR

    def test_v1_shows_the_then_wait(self, app):
        with app.app_context():
            default = make_default()
            step = default.steps[0]
            step.then_wait, step.wait_min, step.wait_max = 7 * HOUR, 6 * HOUR, 8 * HOUR
            db.session.commit()
        v1 = app.test_client().get('/api/v1/recipes').json['data'][0]
        assert v1['steps'][0]['then_wait'] == 7 * HOUR

    def test_steps_written_by_the_previous_version_still_work(self, app):
        # m2h doesn't know then_wait, so it leaves it null with wait_min == wait_max
        assert RecipeStep(then_wait=None, wait_min=900, wait_max=900).default_wait == 900


class TestDetail:
    def test_detail_fields_round_trip(self, baker):
        recipe = create(baker, with_steps(
            {"text": "Shape", "then_wait": 3600, "active_seconds": 900, "needs_presence": True},
            {"text": "Proof", "then_wait": 7200, "needs_presence": False},
            detail_level="detailed")).json['recipe']
        assert recipe['detail_level'] == 'detailed'
        assert [(s['active_seconds'], s['needs_presence']) for s in recipe['steps']] == [(900, True), (None, False)]

    def test_new_recipes_are_simple(self, baker):
        recipe = create(baker).json['recipe']
        assert (recipe['detail_level'], recipe['is_draft']) == ('simple', False)

    def test_switching_to_simple_keeps_the_detail(self, baker):
        recipe = create(baker, with_steps({"text": "Shape", "then_wait": 3600, "wait_min": 3000, "wait_max": 4200,
                                           "active_seconds": 900}, detail_level="detailed")).json['recipe']
        body = {**RECIPE, "detail_level": "simple", "steps": [
            {key: recipe['steps'][0][key] for key in ('id', 'text', 'then_wait', 'wait_min', 'wait_max', 'active_seconds')}]}
        updated = baker.put(f"/api/v2/recipes/{recipe['id']}", json=body).json['recipe']
        assert updated['detail_level'] == 'simple'
        assert (updated['steps'][0]['wait_min'], updated['steps'][0]['active_seconds']) == (3000, 900)

    def test_hands_on_longer_than_the_wait_is_flagged(self, baker):
        step = step_of(baker, {"text": "Laminate", "then_wait": 600, "active_seconds": 1200})
        assert step['warnings'] == ['hands_on_longer_than_wait']

    def test_validation(self, baker):
        response = create(baker, with_steps(
            {"text": "a", "then_wait": -1},
            {"text": "b", "wait_min": 600, "wait_max": 300},
            {"text": "c", "active_seconds": True},
            {"text": "d", "needs_presence": "yes"},
            detail_level="fancy"))
        assert response.status_code == 400
        assert set(response.json['fields']) == {'detail_level', 'steps[0].then_wait', 'steps[1].wait_max',
                                                'steps[2].active_seconds', 'steps[3].needs_presence'}

    def test_the_database_enforces_the_basics(self, app, client):
        with app.app_context():
            default = make_default()
            for field, value in (('then_wait', -1), ('active_seconds', -1)):
                setattr(default.steps[0], field, value)
                with raises(IntegrityError):
                    db.session.commit()
                db.session.rollback()
            default.detail_level = 'fancy'
            with raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


DRAFT = {"is_draft": True, "name": "", "steps": [{"text": ""}, {"text": "Bake", "then_wait": 2700}]}


class TestDrafts:
    def test_a_draft_saves_incomplete(self, baker):
        response = create(baker, DRAFT)
        assert response.status_code == 201
        recipe = response.json['recipe']
        assert recipe['is_draft'] is True
        assert recipe['name'] == '' and recipe['slug'] == 'recipe'

    def test_drafts_still_check_types_and_ranges(self, baker):
        response = create(baker, {**DRAFT, "steps": [{"text": 5, "wait_min": 600, "wait_max": 60}]})
        assert set(response.json['fields']) == {'steps[0].text', 'steps[0].wait_max'}

    def test_only_the_owner_sees_a_draft(self, app, baker, other):
        draft = create(baker, DRAFT).json['recipe']
        suffix = draft['path'].rsplit('-', 1)[1]

        assert baker.get(f"/api/v2/recipes/{draft['id']}").status_code == 200
        assert [r['id'] for r in baker.get('/api/v2/recipes').json['recipes']] == [draft['id']]
        for browser in (other, app.test_client()):
            assert browser.get(f"/api/v2/recipes/{draft['id']}").status_code == 404
            assert browser.get(f"/api/v2/recipes/by-suffix/{suffix}").status_code == 404
            assert browser.get('/api/v2/recipes').json['recipes'] == []
        assert other.post(f"/api/v2/recipes/{draft['id']}/copy", json={}).status_code == 404

    def test_going_live_needs_a_valid_recipe(self, baker):
        draft = create(baker, DRAFT).json['recipe']
        incomplete = baker.put(f"/api/v2/recipes/{draft['id']}", json={**DRAFT, "is_draft": False})
        assert incomplete.status_code == 400
        assert set(incomplete.json['fields']) == {'name', 'steps[0].text'}

        live = baker.put(f"/api/v2/recipes/{draft['id']}", json={**RECIPE, "is_draft": False}).json['recipe']
        assert live['is_draft'] is False and live['slug'] == 'weekend-rye'

    def test_drafts_cant_be_published(self, baker):
        draft = create(baker, {**RECIPE, "is_draft": True}).json['recipe']
        response = baker.post(f"/api/v2/recipes/{draft['id']}/publish", json={})
        assert response.status_code == 409
        assert response.json['code'] == 'recipe_is_draft'

    def test_a_published_recipe_cant_go_back_to_draft(self, baker):
        recipe = create(baker).json['recipe']
        baker.post(f"/api/v2/recipes/{recipe['id']}/publish", json={})
        response = baker.put(f"/api/v2/recipes/{recipe['id']}", json={**RECIPE, "is_draft": True})
        assert response.status_code == 409
        assert response.json['code'] == 'recipe_published'

    def test_copying_your_own_draft_makes_another_draft(self, baker):
        draft = create(baker, DRAFT).json['recipe']
        copy = baker.post(f"/api/v2/recipes/{draft['id']}/copy", json={}).json['recipe']
        assert copy['is_draft'] is True and copy['source_recipe_id'] == draft['id']

    def test_defaults_are_never_drafts(self, app, client, admin_headers):
        response = client.post('/api/v2/admin/recipes', json={**RECIPE, "is_draft": True}, headers=admin_headers)
        assert response.status_code == 400
        assert set(response.json['fields']) == {'is_draft'}

        with app.app_context():
            default = make_default()
            default.is_draft = True
            with raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_the_database_refuses_a_published_draft(self, app, baker):
        draft_id = create(baker, DRAFT).json['recipe']['id']
        with app.app_context():
            recipe = db.session.get(Recipe, UUID(draft_id))
            recipe.published_at = utc_now()
            with raises(IntegrityError):
                db.session.commit()
            db.session.rollback()
