"""Tests for v2 recipes (breadsheet#29): scopes, permissions, copying, slugs and suffixes, and lookups."""
from backend.database import db
from backend.models import Recipe, RecipeStep, utc_now
from backend.slugs import is_public_suffix
from json import dumps
from pytest import fixture
from sqlalchemy import select

RECIPE = {
    "name":       "Weekend Rye",
    "author":     "Me",
    "difficulty": "Intermediate",
    "steps":      [{"text": "Mix", "note": "warm water", "wait_min": 1800},
                   {"text": "Proof", "wait_min": 3600, "wait_max": 5400}]
}


def make_default(name="Country Sourdough", slug="country-sourdough", waits=(1800, 3600)) -> Recipe:
    now = utc_now()
    recipe = Recipe(name=name, slug=slug, date_added=now, start_time=now, last_modified=now,
                    steps=[RecipeStep(position=i, text=f"Step {i}", wait_min=w, wait_max=w)
                           for i, w in enumerate(waits, start=1)])
    db.session.add(recipe)
    db.session.commit()
    return recipe


def register(client, username):
    response = client.post('/api/v2/users', json={'username': username})
    assert response.status_code == 201
    return response.json['user']


@fixture
def baker(client):
    """The test client, signed in as `baker`."""
    register(client, 'baker')
    return client


@fixture
def other(app, client):
    """A second browser, signed in as `other`."""
    browser = app.test_client()
    register(browser, 'other')
    return browser


def create(client, body=None):
    return client.post('/api/v2/recipes', json=body or RECIPE)


class TestCreate:
    def test_creates_a_personal_recipe(self, baker):
        response = create(baker)
        assert response.status_code == 201
        recipe = response.json['recipe']

        assert recipe['scope'] == 'personal'
        assert recipe['owner'] == 'baker'
        assert recipe['is_mine'] is True
        assert recipe['slug'] == 'weekend-rye'
        suffix = recipe['path'].rsplit('-', 1)[1]
        assert is_public_suffix(suffix)
        assert recipe['path'] == f'/recipes/weekend-rye-{suffix}'
        assert recipe['length_seconds'] == 1800 + 4500  # Proof has a range and no Then Wait: the middle
        assert recipe['length_max_seconds'] == 1800 + 5400
        assert [s['text'] for s in recipe['steps']] == ['Mix', 'Proof']
        assert recipe['steps'][0]['wait_max'] == 1800  # one wait means min == max
        assert recipe['steps'][1]['wait_max'] == 5400
        assert 'solve_for_start' not in recipe and 'start_time' not in recipe

    def test_needs_a_signed_in_browser(self, client):
        response = create(client)
        assert response.status_code == 401
        assert response.json['code'] == 'not_signed_in'

    def test_validation_reports_each_field(self, baker):
        response = create(baker, {
            "name":  " ",
            "url":   "javascript:alert(1)",
            "steps": [{"text": "", "wait_min": -5}, {"text": "ok", "wait_min": 600, "wait_max": 60}]
        })
        assert response.status_code == 400
        assert response.json['code'] == 'recipe_invalid'
        assert set(response.json['fields']) == {
            'name', 'url', 'steps[0].text', 'steps[0].wait_min', 'steps[1].wait_max'}

    def test_limits(self, baker):
        assert create(baker, {"name": "x" * 201}).status_code == 400
        assert create(baker, {"name": "Long", "steps": [{"text": "s"}] * 101}).status_code == 400
        assert create(baker, {"name": "Long", "steps": [{"text": "s", "wait_min": 31 * 86400}]}).status_code == 400
        assert create(baker, {"name": "Bad level", "difficulty": "Impossible"}).status_code == 400

    def test_requires_json(self, baker):
        assert baker.post('/api/v2/recipes', data=dumps(RECIPE), content_type='text/plain').status_code == 415


class TestRead:
    def test_list_has_defaults_then_only_my_own(self, baker, other):
        make_default()
        create(baker)
        create(other, {**RECIPE, "name": "Someone Else's Rye"})

        names = [r['name'] for r in baker.get('/api/v2/recipes').json['recipes']]
        assert names == ['Country Sourdough', 'Weekend Rye']

    def test_signed_out_list_is_defaults_only(self, app, baker):
        make_default()
        create(baker)
        recipes = app.test_client().get('/api/v2/recipes').json['recipes']
        assert [r['scope'] for r in recipes] == ['default']
        assert 'steps' not in recipes[0]  # summaries only

    def test_search_by_name(self, baker):
        make_default()
        create(baker)
        assert [r['name'] for r in baker.get('/api/v2/recipes?q=rye').json['recipes']] == ['Weekend Rye']
        assert baker.get('/api/v2/recipes?q=100%25').json['recipes'] == []  # % is literal

    def test_anyone_with_the_link_can_view_a_personal_recipe(self, app, baker):
        recipe = create(baker).json['recipe']
        response = app.test_client().get(f"/api/v2/recipes/{recipe['id']}")
        assert response.status_code == 200
        assert response.json['recipe']['is_mine'] is False
        assert response.json['recipe']['owner'] == 'baker'

    def test_unknown_ids(self, client):
        assert client.get('/api/v2/recipes/not-a-uuid').status_code == 404
        assert client.get('/api/v2/recipes/0190a8e7-0000-7000-8000-000000000000').json['code'] == 'not_found'


class TestEditAndDelete:
    def test_owner_edits_and_rename_keeps_the_suffix(self, baker):
        recipe = create(baker).json['recipe']
        suffix = recipe['path'].rsplit('-', 1)[1]
        mix_id = recipe['steps'][0]['id']

        response = baker.put(f"/api/v2/recipes/{recipe['id']}", json={
            **RECIPE, "name": "Sunday Rye",
            "steps": [{"id": mix_id, "text": "Mix well", "wait_min": 900}]})
        assert response.status_code == 200
        updated = response.json['recipe']
        assert updated['slug'] == 'sunday-rye'
        assert updated['path'] == f'/recipes/sunday-rye-{suffix}'
        assert updated['steps'] == [{"id": mix_id, "position": 1, "text": "Mix well", "note": None,
                                     "then_wait": 900, "wait_min": 900, "wait_max": 900, "default_wait": 900,
                                     "active_seconds": None, "needs_presence": None, "warnings": []}]

    def test_others_cant_edit_or_delete(self, baker, other):
        recipe_id = create(baker).json['recipe']['id']
        for response in (other.put(f'/api/v2/recipes/{recipe_id}', json=RECIPE),
                         other.delete(f'/api/v2/recipes/{recipe_id}', json={})):
            assert response.status_code == 403
            assert response.json['code'] == 'not_owner'

    def test_defaults_are_read_only(self, baker):
        default = make_default()
        response = baker.put(f'/api/v2/recipes/{default.id}', json=RECIPE)
        assert response.status_code == 403
        assert response.json['code'] == 'default_read_only'
        assert baker.delete(f'/api/v2/recipes/{default.id}', json={}).json['code'] == 'default_read_only'

    def test_owner_deletes(self, baker):
        recipe_id = create(baker).json['recipe']['id']
        assert baker.delete(f'/api/v2/recipes/{recipe_id}', json={}).status_code == 204
        assert baker.get(f'/api/v2/recipes/{recipe_id}').status_code == 404

    def test_signed_out_writes_are_refused(self, app, baker):
        recipe_id = create(baker).json['recipe']['id']
        assert app.test_client().put(f'/api/v2/recipes/{recipe_id}', json=RECIPE).status_code == 401


class TestCopy:
    def test_make_a_default_mine(self, baker):
        default = make_default()
        response = baker.post(f'/api/v2/recipes/{default.id}/copy', json={})
        assert response.status_code == 201
        copy = response.json['recipe']

        assert copy['scope'] == 'personal' and copy['is_mine'] is True
        assert copy['source_recipe_id'] == str(default.id)
        assert copy['slug'] == 'country-sourdough'
        assert copy['path'] != '/recipes/country-sourdough'  # personal URLs carry a suffix
        assert [s['wait_min'] for s in copy['steps']] == [1800, 3600]
        assert copy['id'] != str(default.id)
        assert {s['id'] for s in copy['steps']}.isdisjoint({str(s.id) for s in default.steps})

    def test_copies_are_independent(self, baker, other):
        source = create(baker).json['recipe']
        copy = other.post(f"/api/v2/recipes/{source['id']}/copy", json={}).json['recipe']

        other.put(f"/api/v2/recipes/{copy['id']}", json={**RECIPE, "name": "My Rye"})
        assert baker.get(f"/api/v2/recipes/{source['id']}").json['recipe']['name'] == 'Weekend Rye'

        # Deleting the source leaves the copy, with no link back
        baker.delete(f"/api/v2/recipes/{source['id']}", json={})
        assert other.get(f"/api/v2/recipes/{copy['id']}").json['recipe']['source_recipe_id'] is None

    def test_needs_a_signed_in_browser(self, app, client):
        with app.app_context():  # no request has opened one yet
            default_id = make_default().id
        assert client.post(f'/api/v2/recipes/{default_id}/copy', json={}).status_code == 401


class TestLookups:
    def test_by_slug_finds_defaults_only(self, baker):
        make_default()
        create(baker, {**RECIPE, "name": "Country Sourdough"})  # same slug, but personal

        response = baker.get('/api/v2/recipes/by-slug/country-sourdough')
        assert response.status_code == 200
        assert response.json['recipe']['scope'] == 'default'
        assert baker.get('/api/v2/recipes/by-slug/nope').status_code == 404

    def test_by_suffix_returns_the_current_slug(self, app, baker):
        recipe = create(baker).json['recipe']
        suffix = recipe['path'].rsplit('-', 1)[1]
        baker.put(f"/api/v2/recipes/{recipe['id']}", json={**RECIPE, "name": "Renamed Rye"})

        response = app.test_client().get(f'/api/v2/recipes/by-suffix/{suffix}')
        assert response.status_code == 200
        assert response.json['recipe']['slug'] == 'renamed-rye'
        assert app.test_client().get('/api/v2/recipes/by-suffix/BAD!').status_code == 404
        assert app.test_client().get('/api/v2/recipes/by-suffix/zzzzzz').status_code == 404


def test_personal_recipes_never_reach_v1(baker):
    """The spec's rule: v1 only ever returns default recipes."""
    make_default()
    personal_id = create(baker).json['recipe']['id']

    names = [r['name'] for r in baker.get('/api/v1/recipes').json['data']]
    assert names == ['Country Sourdough']
    assert baker.get(f'/api/v1/recipe/{personal_id}').status_code == 404
    assert db.session.scalar(select(Recipe).where(Recipe.name == 'Weekend Rye')) is not None
