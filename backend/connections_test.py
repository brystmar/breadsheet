"""Tests for Home Assistant pairing, device tokens, scopes, and connections (breadsheet#27)."""
import re
from backend.bakes_test import LOAF, at, baker, clock, loaf, other  # noqa: F401 (fixtures)
from backend.database import db
from backend.models import Bake, Connection, Event, PairingCode
from backend.recipe_routes_v2_test import create, register
from datetime import timedelta
from sqlalchemy import select

CODE = re.compile(r'^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$')


def issue_code(browser) -> str:
    response = browser.post('/api/v2/pairing-codes', json={})
    assert response.status_code == 201, response.json
    return response.json['code']


def pair(app, code, label='Kitchen HA'):
    return app.test_client().post('/api/v2/devices', json={'code': code, 'label': label})


def paired_token(app, browser) -> str:
    response = pair(app, issue_code(browser))
    assert response.status_code == 201, response.json
    return response.json['token']


def as_device(app, token):
    """A client with no cookies that sends the device token, like Home Assistant."""
    client = app.test_client()
    headers = {'Authorization': f'Bearer {token}'}
    return client, headers


class TestPairingCodes:
    def test_a_code_is_xxxx_xxxx_for_ten_minutes(self, baker):
        response = baker.post('/api/v2/pairing-codes', json={})
        assert response.status_code == 201
        assert CODE.match(response.json['code'])
        assert 'expires_at' in response.json

    def test_only_its_hash_is_stored(self, app, baker):
        code = issue_code(baker)
        with app.app_context():
            stored = db.session.scalars(select(PairingCode)).one()
            assert code.replace('-', '').encode() not in stored.code_hash
            assert len(stored.code_hash) == 32

    def test_a_new_code_voids_the_old_one(self, app, baker):
        first, second = issue_code(baker), issue_code(baker)
        assert pair(app, first).json['code'] == 'pairing_code_invalid'
        assert pair(app, second).status_code == 201

    def test_signed_out_gets_no_code(self, app, client):
        assert app.test_client().post('/api/v2/pairing-codes', json={}).status_code == 401


class TestPairing:
    def test_a_code_becomes_a_device_token_with_all_four_scopes(self, app, baker):
        response = pair(app, issue_code(baker), label='  Kitchen   HA  ')
        assert response.status_code == 201
        assert len(response.json['token']) >= 43  # 256 bits, URL-safe base64
        connection = response.json['connection']
        assert connection['label'] == 'Kitchen HA'
        assert connection['scopes'] == ['recipes:read', 'recipes:write', 'bakes:read', 'bakes:write']
        assert response.json['user']['username'] == 'baker'  # HA keys its config entry on the user id
        with app.app_context():
            stored = db.session.scalars(select(Connection)).one()
            assert response.json['token'].encode() not in stored.token_hash

    def test_codes_are_read_forgivingly(self, app, baker):
        code = issue_code(baker)
        typed = code.replace('-', '').lower().replace('1', 'l').replace('0', 'o')
        assert pair(app, typed).status_code == 201

    def test_a_label_is_optional(self, app, baker):
        response = app.test_client().post('/api/v2/devices', json={'code': issue_code(baker)})
        assert response.json['connection']['label'] == 'Home Assistant'

    def test_a_code_works_once(self, app, baker):
        code = issue_code(baker)
        assert pair(app, code).status_code == 201
        assert pair(app, code).json['code'] == 'pairing_code_invalid'

    def test_an_expired_code_fails(self, app, baker, monkeypatch):
        code = issue_code(baker)
        from backend import connection_routes
        later = connection_routes.utc_now() + timedelta(minutes=11)
        monkeypatch.setattr('backend.connection_routes.utc_now', lambda: later)
        assert pair(app, code).json['code'] == 'pairing_code_invalid'

    def test_failed_attempts_are_rate_limited(self, app, baker):
        for _ in range(5):
            assert pair(app, 'ZZZZ-ZZZZ').status_code == 400
        assert pair(app, issue_code(baker)).status_code == 429


class TestDeviceTokens:
    def test_a_token_reads_and_writes_bakes_as_its_user(self, app, baker, loaf, clock):
        token = paired_token(app, baker)
        device, headers = as_device(app, token)
        response = device.post('/api/v2/bakes', headers=headers, json={
            "recipe_id": loaf['id'], "anchor_type": "start", "anchor_time": at(1), "time_zone": 'America/Los_Angeles'})
        assert response.status_code == 201, response.json
        assert response.json['bake']['created_via'] == 'ha'
        assert device.get('/api/v2/bakes', headers=headers).json['bakes'][0]['id'] == response.json['bake']['id']
        with app.app_context():
            started = db.session.scalars(select(Event).where(Event.type == 'bake_started')).one()
            assert started.client == 'ha'
            assert db.session.scalars(select(Connection)).one().last_used_at is not None

    def test_a_token_sees_its_users_own_recipes(self, app, baker):
        mine = create(baker).json['recipe']
        device, headers = as_device(app, paired_token(app, baker))
        listed = device.get('/api/v2/recipes', headers=headers).json['recipes']
        assert any(recipe['id'] == mine['id'] and recipe['is_mine'] for recipe in listed)

    def test_a_token_wins_over_the_session_cookie(self, app, baker, other):
        token = paired_token(app, other)
        mine = baker.get('/api/v2/recipes').json['recipes']
        as_other = baker.get('/api/v2/recipes', headers={'Authorization': f'Bearer {token}'}).json['recipes']
        assert [recipe['id'] for recipe in as_other if recipe['is_mine']] == []
        assert len(as_other) == len([recipe for recipe in mine if not recipe['is_mine']])

    def test_a_missing_scope_is_refused(self, app, baker):
        token = paired_token(app, baker)
        with app.app_context():
            connection = db.session.scalars(select(Connection)).one()
            connection.scopes = ['bakes:read']
            db.session.commit()
        device, headers = as_device(app, token)
        assert device.get('/api/v2/bakes', headers=headers).status_code == 200
        response = device.post('/api/v2/recipes', headers=headers, json=LOAF)
        assert response.status_code == 403
        assert response.json['code'] == 'scope_missing'
        assert device.get('/api/v2/recipes', headers=headers).json['code'] == 'scope_missing'

    def test_browser_only_endpoints_refuse_tokens(self, app, baker, loaf):
        device, headers = as_device(app, paired_token(app, baker))
        bake_id = baker.post('/api/v2/bakes', json={"recipe_id": loaf['id'], "anchor_type": "start", "anchor_time": at(1),
                                                    "time_zone": 'America/Los_Angeles'}).json['bake']['id']
        for method, path, body in [('get', '/api/v2/session', None), ('post', '/api/v2/pairing-codes', {}),
                                   ('get', '/api/v2/connections', None),
                                   ('post', '/api/v2/events', {'type': 'ics_exported', 'bake_id': bake_id})]:
            response = getattr(device, method)(path, headers=headers, json=body)
            assert (response.status_code, response.json['code']) == (403, 'scope_missing'), path

    def test_an_unknown_token_is_refused(self, app, client):
        device, headers = as_device(app, 'not-a-real-token')
        response = device.get('/api/v2/bakes', headers=headers)
        assert (response.status_code, response.json['code']) == (401, 'token_invalid')


class TestConnections:
    def test_list_and_revoke(self, app, baker):
        token = paired_token(app, baker)
        connections = baker.get('/api/v2/connections').json['connections']
        assert [connection['label'] for connection in connections] == ['Kitchen HA']
        assert set(connections[0]) == {'id', 'label', 'scopes', 'created_at', 'last_used_at'}

        assert baker.delete(f"/api/v2/connections/{connections[0]['id']}", json={}).status_code == 204
        assert baker.get('/api/v2/connections').json['connections'] == []
        device, headers = as_device(app, token)
        assert device.get('/api/v2/bakes', headers=headers).json['code'] == 'token_invalid'
        assert baker.delete(f"/api/v2/connections/{connections[0]['id']}", json={}).status_code == 404

    def test_only_your_own(self, app, baker, other):
        paired_token(app, baker)
        connection_id = baker.get('/api/v2/connections').json['connections'][0]['id']
        assert other.get('/api/v2/connections').json['connections'] == []
        assert other.delete(f'/api/v2/connections/{connection_id}', json={}).status_code == 404
        assert other.delete('/api/v2/connections/not-a-uuid', json={}).status_code == 404
        assert other.patch(f'/api/v2/connections/{connection_id}', json={'label': 'Mine'}).status_code == 404
        assert other.patch('/api/v2/connections/not-a-uuid', json={'label': 'Mine'}).status_code == 404


class TestRename:
    """Renaming a connection (breadsheet#97)."""

    def connection_id(self, app, baker) -> str:
        paired_token(app, baker)
        return baker.get('/api/v2/connections').json['connections'][0]['id']

    def test_rename(self, app, baker):
        connection_id = self.connection_id(app, baker)
        response = baker.patch(f'/api/v2/connections/{connection_id}', json={'label': '  Cabin \t HA  '})
        assert response.status_code == 200, response.json
        assert response.json['connection']['label'] == 'Cabin HA'
        assert set(response.json['connection']) == {'id', 'label', 'scopes', 'created_at', 'last_used_at'}
        assert baker.get('/api/v2/connections').json['connections'][0]['label'] == 'Cabin HA'

    def test_sixty_characters_is_the_limit(self, app, baker):
        connection_id = self.connection_id(app, baker)
        assert baker.patch(f'/api/v2/connections/{connection_id}', json={'label': 'x' * 60}).status_code == 200
        for label in ['', '   ', 'x' * 61]:
            response = baker.patch(f'/api/v2/connections/{connection_id}', json={'label': label})
            assert (response.status_code, response.json['code']) == (400, 'label_invalid'), label
        assert baker.get('/api/v2/connections').json['connections'][0]['label'] == 'x' * 60

    def test_a_label_must_be_text(self, app, baker):
        connection_id = self.connection_id(app, baker)
        for body in [{}, {'label': None}, {'label': 7}]:
            response = baker.patch(f'/api/v2/connections/{connection_id}', json=body)
            assert (response.status_code, response.json['code']) == (400, 'body_invalid'), body

    def test_revoked_connections_cant_be_renamed(self, app, baker):
        connection_id = self.connection_id(app, baker)
        baker.delete(f'/api/v2/connections/{connection_id}', json={})
        response = baker.patch(f'/api/v2/connections/{connection_id}', json={'label': 'Gone'})
        assert (response.status_code, response.json['code']) == (404, 'not_found')

    def test_only_a_browser_can_rename(self, app, baker):
        token = paired_token(app, baker)
        connection_id = baker.get('/api/v2/connections').json['connections'][0]['id']
        device, headers = as_device(app, token)
        response = device.patch(f'/api/v2/connections/{connection_id}', headers=headers, json={'label': 'Sneaky'})
        assert (response.status_code, response.json['code']) == (403, 'scope_missing')

    def test_signed_out(self, app, baker):
        connection_id = self.connection_id(app, baker)
        response = app.test_client().patch(f'/api/v2/connections/{connection_id}', json={'label': 'Nope'})
        assert (response.status_code, response.json['code']) == (401, 'not_signed_in')

    def test_deleting_a_user_removes_their_connections(self, app, client):
        user = register(client, 'pairer')
        paired_token(app, client)
        with app.app_context():
            from backend.models import User
            db.session.delete(db.session.get(User, user['id']))
            db.session.commit()
            assert db.session.scalars(select(Connection)).all() == []


def test_bakes_started_in_a_browser_say_web(app, baker, loaf, clock):
    response = baker.post('/api/v2/bakes', json={"recipe_id": loaf['id'], "anchor_type": "start", "anchor_time": at(1),
                                                 "time_zone": 'America/Los_Angeles'})
    with app.app_context():
        assert db.session.get(Bake, response.json['bake']['id']).created_via == 'web'


def test_metrics_count_bakes_started_while_ha_was_paired(app, client):
    """Real time throughout: the metric compares the bake's start with the connection's pairing."""
    from backend.metrics import run_metrics
    from datetime import datetime, timezone
    register(client, 'metric-baker')
    recipe = create(client, LOAF).json['recipe']
    start = lambda: client.post('/api/v2/bakes', json={  # noqa: E731
        "recipe_id": recipe['id'], "anchor_type": "start", "time_zone": 'America/Los_Angeles',
        "anchor_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
    assert start().status_code == 201          # before pairing
    paired_token(app, client)
    assert start().status_code == 201          # while paired
    with app.app_context():
        assert run_metrics(db.session)['bakes_with_ha'] == [{'with_ha_paired': 1, 'fancy_bakes': 0, 'bakes': 2}]
