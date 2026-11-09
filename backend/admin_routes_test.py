"""Tests for the admin endpoints (breadsheet#28): the admin key, and creating and editing defaults."""
import logging
from backend.database import db
from backend.connections_test import as_device, paired_token
from backend.models import Recipe, User
from backend.recipe_routes_v2_test import RECIPE, create, register
from sqlalchemy import select


def admin_create(client, headers, body=None):
    return client.post('/api/v2/admin/recipes', json=body or RECIPE, headers=headers)


class TestAdminKey:
    def test_requests_without_the_key_are_refused(self, client):
        for headers in ({'Authorization': 'Bearer wrong-key'}, {'Authorization': 'test-only-admin-key'},
                        {'Authorization': 'Basic test-only-admin-key'}, {'Authorization': 'Bearer '}):
            response = admin_create(client, headers)
            assert response.status_code == 401, headers
            assert response.json['code'] == 'admin_key_invalid'
        response = admin_create(client, {})  # no key and no session (breadsheet#86)
        assert (response.status_code, response.json['code']) == (401, 'not_signed_in')
        assert db.session.scalar(select(Recipe)) is None

    def test_a_signed_in_user_is_not_an_admin(self, client):
        register(client, 'baker')
        response = admin_create(client, {})
        assert (response.status_code, response.json['code']) == (403, 'admin_required')

    def test_unconfigured_or_malformed_hash_refuses_everything(self, app, client, admin_headers, monkeypatch, caplog):
        monkeypatch.setitem(app.config, 'ADMIN_KEY_HASH', None)
        assert admin_create(client, admin_headers).status_code == 401

        monkeypatch.setitem(app.config, 'ADMIN_KEY_HASH', 'not-hex')
        assert admin_create(client, admin_headers).status_code == 401
        assert any(r.levelname == 'ERROR' and 'ADMIN_KEY_HASH' in r.message for r in caplog.records)

    def test_failed_attempts_are_rate_limited(self, client, admin_headers):
        for _ in range(10):
            assert admin_create(client, {'Authorization': 'Bearer guess'}).status_code == 401

        response = admin_create(client, admin_headers)  # even the right key, once over the limit
        assert response.status_code == 429
        assert response.json['code'] == 'rate_limited'
        assert int(response.headers['Retry-After']) > 0

    def test_the_key_is_never_logged(self, client, admin_headers, caplog):
        caplog.set_level(logging.DEBUG)
        admin_create(client, admin_headers)
        admin_create(client, {'Authorization': 'Bearer a-distinctive-wrong-key'})
        assert 'test-only-admin-key' not in caplog.text
        assert 'a-distinctive-wrong-key' not in caplog.text


class TestCreateDefault:
    def test_creates_a_default_everyone_sees(self, app, client, admin_headers):
        response = admin_create(client, admin_headers)
        assert response.status_code == 201
        recipe = response.json['recipe']

        assert recipe['scope'] == 'default'
        assert recipe['owner'] is None and recipe['is_mine'] is False
        assert recipe['path'] == '/recipes/weekend-rye'
        assert [s['text'] for s in recipe['steps']] == ['Mix', 'Proof']

        signed_out = app.test_client()
        assert [r['name'] for r in signed_out.get('/api/v2/recipes').json['recipes']] == ['Weekend Rye']
        assert [r['name'] for r in signed_out.get('/api/v1/recipes').json['data']] == ['Weekend Rye']

    def test_slugs_are_unique_among_defaults(self, client, admin_headers):
        admin_create(client, admin_headers)
        assert admin_create(client, admin_headers).json['recipe']['slug'] == 'weekend-rye-2'

    def test_validates_like_personal_recipes(self, client, admin_headers):
        response = admin_create(client, admin_headers, {"name": " ", "steps": [{"text": ""}]})
        assert response.status_code == 400
        assert response.json['code'] == 'recipe_invalid'
        assert set(response.json['fields']) == {'name', 'steps[0].text'}

    def test_requires_json(self, client, admin_headers):
        response = client.post('/api/v2/admin/recipes', data='{}', content_type='text/plain', headers=admin_headers)
        assert response.status_code == 415


class TestEditDefault:
    def test_rename_keeps_the_slug_and_step_ids(self, client, admin_headers):
        created = admin_create(client, admin_headers).json['recipe']
        mix_id = created['steps'][0]['id']

        response = client.put(f"/api/v2/admin/recipes/{created['id']}", headers=admin_headers, json={
            **RECIPE, "name": "Weekday Rye", "steps": [{"id": mix_id, "text": "Mix well", "wait_min": 900}]})
        assert response.status_code == 200
        updated = response.json['recipe']
        assert updated['name'] == 'Weekday Rye'
        assert updated['slug'] == 'weekend-rye'  # default URLs never change
        assert [(s['id'], s['text']) for s in updated['steps']] == [(mix_id, 'Mix well')]
        assert updated['updated_at'] != created['updated_at']

    def test_personal_recipes_dont_exist_here(self, client, admin_headers):
        register(client, 'baker')
        personal_id = create(client).json['recipe']['id']
        response = client.put(f'/api/v2/admin/recipes/{personal_id}', headers=admin_headers, json=RECIPE)
        assert response.status_code == 404
        assert client.get(f'/api/v2/recipes/{personal_id}').json['recipe']['name'] == 'Weekend Rye'

    def test_unknown_ids(self, client, admin_headers):
        assert client.put('/api/v2/admin/recipes/nope', headers=admin_headers, json=RECIPE).status_code == 404

    def test_needs_the_key(self, client, admin_headers):
        recipe_id = admin_create(client, admin_headers).json['recipe']['id']
        assert client.put(f'/api/v2/admin/recipes/{recipe_id}', json=RECIPE).status_code == 401


# breadsheet#86: admins are users with is_admin, signed in like anyone else
def make_admin(app, username):
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == username))
        user.is_admin = True
        db.session.commit()


class TestAdminSessions:
    def test_a_signed_in_admin_can_curate_defaults(self, app, client):
        register(client, 'chief')
        make_admin(app, 'chief')

        created = admin_create(client, {})
        assert created.status_code == 201, created.json
        recipe_id = created.json['recipe']['id']
        assert created.json['recipe']['scope'] == 'default'
        assert client.put(f'/api/v2/admin/recipes/{recipe_id}', json=RECIPE).status_code == 200
        assert client.delete(f'/api/v2/admin/recipes/{recipe_id}', json={}).status_code == 204

    def test_the_session_says_who_is_an_admin(self, app, client):
        register(client, 'chief')
        assert client.get('/api/v2/session').json['user']['is_admin'] is False
        make_admin(app, 'chief')
        assert client.get('/api/v2/session').json['user']['is_admin'] is True

    def test_signup_never_makes_an_admin(self, client):
        response = client.post('/api/v2/users', json={'username': 'hopeful', 'is_admin': True})
        assert response.json['user']['is_admin'] is False

    def test_an_admins_own_device_token_is_not_an_admin(self, app, client):
        register(client, 'chief')
        make_admin(app, 'chief')
        token = paired_token(app, client)
        device, headers = as_device(app, token)
        response = device.post('/api/v2/admin/recipes', json=RECIPE, headers=headers)
        assert (response.status_code, response.json['code']) == (403, 'scope_missing')
        with app.app_context():
            assert db.session.scalar(select(Recipe)) is None

    def test_the_admin_list_has_every_default_archived_last(self, app, client, admin_headers):
        register(client, 'chief')
        make_admin(app, 'chief')
        ids = {name: admin_create(client, {}, {**RECIPE, 'name': name}).json['recipe']['id']
               for name in ['Bagels', 'Ciabatta', 'Anadama']}
        client.delete(f"/api/v2/admin/recipes/{ids['Anadama']}", json={})
        create(client)  # a personal recipe never shows here

        listed = client.get('/api/v2/admin/recipes').json['recipes']
        assert [(r['name'], r['archived_at'] is not None) for r in listed] == [
            ('Bagels', False), ('Ciabatta', False), ('Anadama', True)]
        assert app.test_client().get('/api/v2/admin/recipes', headers=admin_headers).status_code == 200

    def test_the_admin_list_is_for_admins_only(self, app, client):
        assert app.test_client().get('/api/v2/admin/recipes').json['code'] == 'not_signed_in'
        register(client, 'baker')
        assert client.get('/api/v2/admin/recipes').json['code'] == 'admin_required'
