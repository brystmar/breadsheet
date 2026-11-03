"""Tests for the v1 replacement endpoints, against the local test Postgres."""
from json import dumps


def put(client, scope, old, data: dict):
    return client.put(f'/api/v1/replacements/{scope}/{old}', data=dumps(data))


def seed(client):
    for scope, old, new in (("ingredients", "ounces", "oz"),
                            ("ingredients", "Tablespoon", "Tbsp"),
                            ("ingredients", "½", "1/2"),
                            ("ingredients", "cup", "c"),
                            ("directions", "°F", " degrees F"),
                            ("directions", "Preheat", "Heat")):
        assert put(client, scope, old, {"scope": scope, "old": old, "new": new}).status_code == 201


class TestReplacementCollectionApi:
    def test_get_empty(self, client):
        response = client.get('/api/v1/replacements/all')
        assert response.status_code == 200
        assert response.json == {'message': 'Success', 'data': {}}

    def test_get_all_in_byte_order(self, client):
        seed(client)
        response = client.get('/api/v1/replacements/all')
        assert response.status_code == 200

        # Byte order, as DynamoDB sorted its range key: uppercase before lowercase, non-ASCII last
        data = response.json['data']
        assert [r['old'] for r in data['ingredients']] == ["Tablespoon", "cup", "ounces", "½"]
        assert [r['old'] for r in data['directions']] == ["Preheat", "°F"]
        assert data['ingredients'][0] == {"scope": "ingredients", "old": "Tablespoon", "new": "Tbsp"}
        assert list(data) == ["ingredients", "directions"]

    def test_get_one_scope(self, client):
        seed(client)
        response = client.get('/api/v1/replacements/directions')
        assert response.status_code == 200
        assert list(response.json['data']) == ['directions']

    def test_get_invalid_scope(self, client):
        response = client.get('/api/v1/replacements/toppings')
        assert response.status_code == 404
        assert response.json == {'message': 'Error', 'data': 'Invalid scope: toppings'}

    def test_put_update(self, client):
        seed(client)
        response = put(client, "ingredients", "cup", {"new": "C"})
        assert response.status_code == 200
        assert response.json == {'message': 'Success', 'data': 'Replacement record updated.'}

        ingredients = client.get('/api/v1/replacements/ingredients').json['data']['ingredients']
        assert {"scope": "ingredients", "old": "cup", "new": "C"} in ingredients

    def test_put_invalid_scope(self, client):
        response = put(client, "toppings", "cup", {"scope": "toppings", "old": "cup", "new": "c"})
        assert response.status_code == 422
        assert response.json == {'message': 'Validation Error', 'data': 'Invalid scope: toppings.'}

    def test_put_missing_fields(self, client):
        response = put(client, "ingredients", "cup", {"new": "c"})
        assert response.status_code == 500
        assert response.json == {'message': 'Error', 'data': 'Error adding scope: ingredients, old: cup, new: c.'}

    def test_delete(self, client):
        seed(client)
        response = client.delete('/api/v1/replacements/ingredients/cup')
        assert response.status_code == 200
        assert response.json == {'message': 'Success',
                                 'data': '<Replacement Text | scope: ingredients, old: cup, new: c> '
                                         'deleted successfully.'}

        response = client.delete('/api/v1/replacements/ingredients/cup')
        assert response.status_code == 404
        assert response.json == {'message': 'Error',
                                 'data': 'Cannot find Replacement w/scope: ingredients, old: cup'}
