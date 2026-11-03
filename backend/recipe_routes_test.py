"""Tests for the v1 recipe endpoints, against the local test Postgres."""
from backend.database import db
from backend.models import Recipe
from datetime import datetime, timezone
from json import dumps
from uuid import UUID, uuid7

RECIPE = {
    "id":              "a-uuid-the-ui-made-up",
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


def post(client, data: dict):
    # The UI sends JSON bodies without a Content-Type header
    return client.post('/api/v1/recipes', data=dumps(data))


def put(client, recipe_id, data: dict):
    return client.put(f'/api/v1/recipe/{recipe_id}', data=dumps(data))


class TestRecipeCollectionApi:
    def test_get_empty(self, client):
        response = client.get('/api/v1/recipes')
        assert response.status_code == 200
        assert response.json == {'message': 'Success', 'data': []}

    def test_post(self, client):
        response = post(client, RECIPE)
        assert response.status_code == 201
        assert response.json['message'] == 'Created'

        data = response.json['data']
        assert UUID(data['id']).version == 7  # the server assigns the id
        assert data['name'] == "Country Sourdough"
        assert data['length'] == 5400

        # POST returns ISO dates; every other endpoint returns epoch ms
        assert data['date_added'] == "2019-02-16T09:00:00+00:00"
        assert data['start_time'] == "2019-02-16T10:00:00+00:00"
        assert data['last_modified'] == data['date_added']
        assert [(s['number'], s['text'], s['then_wait'], s['note']) for s in data['steps']] == \
               [(1, "Mix", 1800, "warm water"), (2, "Fold", 3600, None)]

    def test_post_invalid(self, client):
        response = post(client, {"author": "no name"})
        assert response.status_code == 500
        assert response.json == {'message': 'Error', 'data': 'Other error in parsing args.'}

    def test_get_sorted_by_date_added(self, client):
        for name, date_added in (("Second", 1550394000000), ("Third", 1600624621855), ("First", 1550307600000)):
            post(client, {**RECIPE, "name": name, "date_added": date_added})

        response = client.get('/api/v1/recipes')
        assert response.status_code == 200
        assert [r['name'] for r in response.json['data']] == ["First", "Second", "Third"]
        assert response.json['data'][0]['date_added'] == 1550307600000.0

    def test_get_does_not_write(self, app, client):
        recipe_id = post(client, RECIPE).json['data']['id']
        with app.app_context():
            before = db.session.get(Recipe, UUID(recipe_id)).last_modified

        client.get('/api/v1/recipes')
        client.get(f'/api/v1/recipe/{recipe_id}')

        with app.app_context():
            assert db.session.get(Recipe, UUID(recipe_id)).last_modified == before


class TestRecipeApi:
    def test_get(self, client):
        created = post(client, RECIPE).json['data']

        response = client.get(f"/api/v1/recipe/{created['id']}")
        assert response.status_code == 200
        assert response.json['message'] == 'Success'

        data = response.json['data']
        assert data['id'] == created['id']
        assert data['date_added'] == 1550307600000.0
        assert data['steps'] == created['steps']

    def test_get_not_found(self, client):
        for recipe_id in (uuid7(), "1560122081.000008"):
            response = client.get(f'/api/v1/recipe/{recipe_id}')
            assert response.status_code == 404
            assert response.json == {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}

    def test_put(self, client):
        created = post(client, RECIPE).json['data']
        mix, fold = created['steps']

        # Edit the recipe, update one step, delete another, and add a new one
        updated = {**created,
                   "name":            "Country Sourdough II",
                   "solve_for_start": False,
                   "start_time":      1550400000000,
                   "steps":           [{**mix, "then_wait": 900},
                                       {"step_id": "new", "number": 2, "text": "Bake", "then_wait": 2700}]}
        response = put(client, created['id'], updated)
        assert response.status_code == 200
        assert response.json['message'] == 'Success'

        data = response.json['data']
        assert data['name'] == "Country Sourdough II"
        assert data['solve_for_start'] is False
        assert data['start_time'] == 1550400000000.0
        assert data['date_added'] == 1550307600000.0
        assert data['length'] == 3600
        assert data['steps'][0]['step_id'] == mix['step_id']
        assert data['steps'][1]['step_id'] not in (mix['step_id'], fold['step_id'], "new")
        assert [(s['number'], s['text'], s['then_wait']) for s in data['steps']] == [(1, "Mix", 900), (2, "Bake", 2700)]

        last_modified = datetime.fromtimestamp(data['last_modified'] / 1000, timezone.utc)
        assert abs((datetime.now(timezone.utc) - last_modified).total_seconds()) < 5

        assert client.get(f"/api/v1/recipe/{created['id']}").json['data'] == data

    def test_put_id_mismatch(self, client):
        created = post(client, RECIPE).json['data']

        response = put(client, created['id'], {**created, "id": "something-else"})
        assert response.status_code == 400
        assert response.json['data'] == f"/recipe_id provided to the endpoint ({created['id']}) " \
                                        f"doesn't match the id from the body (something-else)."

    def test_put_not_found(self, client):
        recipe_id = str(uuid7())
        response = put(client, recipe_id, {**RECIPE, "id": recipe_id})
        assert response.status_code == 404
        assert response.json == {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}

    def test_put_invalid(self, client):
        created = post(client, RECIPE).json['data']
        del created['name']

        response = put(client, created['id'], created)
        assert response.status_code == 500
        assert response.json['data'].startswith("Error parsing data into the Recipe model.")
        assert client.get(f"/api/v1/recipe/{created['id']}").json['data']['name'] == "Country Sourdough"

    def test_delete(self, app, client):
        created = post(client, RECIPE).json['data']

        response = client.delete(f"/api/v1/recipe/{created['id']}")
        assert response.status_code == 200
        assert response.json == {'message': 'Success',
                                 'data': f"<Recipe | id: {created['id']}, name: Country Sourdough, length: 5400, "
                                         f"steps: 2> deleted successfully."}

        assert client.get(f"/api/v1/recipe/{created['id']}").status_code == 404
        with app.app_context():
            assert db.session.execute(db.text("SELECT count(*) FROM recipe_steps")).scalar() == 0

    def test_delete_not_found(self, client):
        recipe_id = uuid7()
        response = client.delete(f'/api/v1/recipe/{recipe_id}')
        assert response.status_code == 404
        assert response.json == {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}
