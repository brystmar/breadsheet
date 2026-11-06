"""Tests for the v1 recipe endpoints, against the local test Postgres. v1 is read-only (breadsheet#28)."""
from backend.database import db
from backend.models import Recipe
from pytest import mark
from uuid import UUID, uuid7

RECIPE = {
    "name":            "Country Sourdough",
    "author":          "Chad Robertson",
    "source":          "Tartine Bread",
    "url":             None,
    "difficulty":      "Intermediate",
    "solve_for_start": True,
    "length":          5400,
    "date_added":      1550307600000,  # 2019-02-16T09:00:00Z
    "start_time":      1550311200000,
    "steps":           [{"step_id": 0, "number": 1, "text": "Mix", "then_wait": 1800, "note": "warm water"},
                        {"step_id": 1, "number": 2, "text": "Fold", "then_wait": 3600}]
}


def seed(app, data: dict = RECIPE) -> str:
    """Adds a default recipe from a v1-shaped dict, the way v1 POST used to; returns its id."""
    with app.app_context():
        recipe = Recipe()
        recipe.update_from_v1(data)
        recipe.last_modified = recipe.date_added
        recipe.slug = str(uuid7())  # unique; v1 never shows it
        db.session.add(recipe)
        db.session.commit()
        return str(recipe.id)


class TestRecipeCollectionApi:
    def test_get_empty(self, client):
        response = client.get('/api/v1/recipes')
        assert response.status_code == 200
        assert response.json == {'message': 'Success', 'data': []}

    def test_get_sorted_by_date_added(self, app, client):
        for name, date_added in (("Second", 1550394000000), ("Third", 1600624621855), ("First", 1550307600000)):
            seed(app, {**RECIPE, "name": name, "date_added": date_added})

        response = client.get('/api/v1/recipes')
        assert response.status_code == 200
        assert [r['name'] for r in response.json['data']] == ["First", "Second", "Third"]
        assert response.json['data'][0]['date_added'] == 1550307600000.0
        assert response.json['data'][0]['length'] == 5400

    def test_get_does_not_write(self, app, client):
        recipe_id = seed(app)
        with app.app_context():
            before = db.session.get(Recipe, UUID(recipe_id)).last_modified

        client.get('/api/v1/recipes')
        client.get(f'/api/v1/recipe/{recipe_id}')

        with app.app_context():
            assert db.session.get(Recipe, UUID(recipe_id)).last_modified == before


class TestRecipeApi:
    def test_get(self, app, client):
        recipe_id = seed(app)

        response = client.get(f"/api/v1/recipe/{recipe_id}")
        assert response.status_code == 200
        assert response.json['message'] == 'Success'

        data = response.json['data']
        assert data['id'] == recipe_id
        assert data['date_added'] == 1550307600000.0
        assert data['start_time'] == 1550311200000.0
        assert [(s['number'], s['text'], s['then_wait'], s['note']) for s in data['steps']] == \
               [(1, "Mix", 1800, "warm water"), (2, "Fold", 3600, None)]

    def test_get_not_found(self, client):
        for recipe_id in (uuid7(), "1560122081.000008"):
            response = client.get(f'/api/v1/recipe/{recipe_id}')
            assert response.status_code == 404
            assert response.json == {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}


class TestWritesAreOff:
    """breadsheet#28: defaults are managed with the admin key now, so v1 is read-only."""

    @mark.parametrize('method, path', [
        ('post', '/api/v1/recipes'),
        ('put', '/api/v1/recipe/{id}'),
        ('delete', '/api/v1/recipe/{id}'),
    ])
    def test_writes_return_405_and_change_nothing(self, app, client, method, path):
        recipe_id = seed(app)
        response = getattr(client, method)(path.format(id=recipe_id), json={**RECIPE, "id": recipe_id, "name": "x"})
        assert response.status_code == 405

        recipes = client.get('/api/v1/recipes').json['data']
        assert [(r['id'], r['name']) for r in recipes] == [(recipe_id, "Country Sourdough")]


class TestErrorLogging:
    def test_database_errors_are_logged_at_error_with_traceback(self, client, caplog):
        from sqlalchemy.exc import OperationalError
        from unittest.mock import patch

        outage = OperationalError('SELECT', None, Exception('connection refused'))
        with patch('backend.recipe_routes.db.session.scalars', side_effect=outage):
            response = client.get('/api/v1/recipes')

        assert response.status_code == 500  # unchanged v1 behavior
        errors = [r for r in caplog.records if r.name == 'backend.recipe_routes' and r.levelname == 'ERROR']
        assert errors and errors[0].exc_info is not None
