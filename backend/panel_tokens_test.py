"""Tests for Home Assistant's panel tokens (breadsheet-hass#5)."""
from backend import nudges
from backend.bakes_test import at, baker, clock, loaf, other, started  # noqa: F401 (fixtures)
from backend.connections_test import as_device, paired_token
from backend.database import db
from backend.models import PanelToken
from datetime import timedelta
from pytest import fixture
from sqlalchemy import select


@fixture
def device(app, baker):
    return as_device(app, paired_token(app, baker))


def issue(device, **body):
    client, headers = device
    return client.post('/api/v2/panel-tokens', json=body, headers=headers)


def as_panel(app, token):
    """The website's panel page: no cookies, the panel token as a bearer token."""
    return app.test_client(), {'Authorization': f'Bearer {token}'}


class TestIssuing:
    def test_home_assistant_gets_a_token_and_the_page_to_show(self, app, device):
        response = issue(device)
        assert response.status_code == 201, response.json
        token = response.json['token']
        assert response.json['url'].endswith(f'/panel#t={token}')
        assert len(token) >= 43
        with app.app_context():
            stored = db.session.scalars(select(PanelToken)).one()
            assert token.encode() not in stored.token_hash  # only the hash

    def test_a_bake_can_be_opened_directly(self, device, baker, loaf):
        bake = started(baker, loaf['id'], alert_mode='fancy')
        response = issue(device, bake_id=bake['id'])
        assert f"/panel/{bake['id']}#t=" in response.json['url']

    def test_only_your_own_bakes(self, app, device, other, loaf):
        theirs = started(other, loaf['id'])
        assert issue(device, bake_id=theirs['id']).json['code'] == 'not_found'
        assert issue(device, bake_id='not-a-uuid').json['code'] == 'not_found'

    def test_browsers_and_panel_tokens_cant_get_one(self, app, device, baker):
        assert baker.post('/api/v2/panel-tokens', json={}).json['code'] == 'scope_missing'
        client, headers = as_panel(app, issue(device).json['token'])
        assert client.post('/api/v2/panel-tokens', json={}, headers=headers).json['code'] == 'scope_missing'

    def test_expired_tokens_are_tidied_up(self, app, device, monkeypatch):
        issue(device)
        with app.app_context():
            for panel in db.session.scalars(select(PanelToken)):
                panel.expires_at -= timedelta(hours=13)
            db.session.commit()
        issue(device)
        with app.app_context():
            assert len(db.session.scalars(select(PanelToken)).all()) == 1


class TestUsing:
    def test_the_panel_reads_and_checks_off_bakes(self, app, device, baker, loaf, clock):
        bake = started(baker, loaf['id'], alert_mode='fancy')
        client, headers = as_panel(app, issue(device).json['token'])
        assert [b['id'] for b in client.get('/api/v2/bakes', headers=headers).json['bakes']] == [bake['id']]
        assert client.get(f"/api/v2/bakes/{bake['id']}", headers=headers).status_code == 200
        clock.advance(hours=1)
        response = client.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={'completed_at': at(1)},
                               headers=headers)
        assert response.status_code == 200, response.json
        assert response.json['bake']['steps'][0]['completed_at'] is not None

    def test_bakes_only(self, app, device, loaf, admin_headers):
        client, headers = as_panel(app, issue(device).json['token'])
        for method, path in [('get', '/api/v2/recipes'), ('get', f"/api/v2/recipes/{loaf['id']}"),
                             ('get', '/api/v2/connections'), ('get', '/api/v2/admin/recipes')]:
            response = getattr(client, method)(path, headers=headers)
            assert (response.status_code, response.json['code']) == (403, 'scope_missing'), path
        assert client.post('/api/v2/recipes', json={'name': 'x'}, headers=headers).json['code'] == 'scope_missing'

    def test_it_expires_after_12_hours(self, app, device, monkeypatch):
        client, headers = as_panel(app, issue(device).json['token'])
        with app.app_context():
            for panel in db.session.scalars(select(PanelToken)):
                panel.expires_at -= timedelta(hours=12, seconds=1)
            db.session.commit()
        assert client.get('/api/v2/bakes', headers=headers).json['code'] == 'token_invalid'

    def test_revoking_home_assistant_stops_its_panel(self, app, device, baker):
        client, headers = as_panel(app, issue(device).json['token'])
        connection = baker.get('/api/v2/connections').json['connections'][0]
        baker.delete(f"/api/v2/connections/{connection['id']}", json={})
        assert client.get('/api/v2/bakes', headers=headers).json['code'] == 'token_invalid'

    def test_unknown_tokens_are_refused(self, app):
        client, headers = as_panel(app, 'made-up')
        assert client.get('/api/v2/bakes', headers=headers).json['code'] == 'token_invalid'

    def test_panel_changes_nudge_home_assistant(self, app, device, baker, loaf, clock, monkeypatch):
        sent = []
        monkeypatch.setattr(nudges, 'resolve', lambda host: ['93.184.216.34'])
        monkeypatch.setattr(nudges, 'run_in_background', lambda work: work())
        monkeypatch.setattr(nudges, 'send', lambda url, address: sent.append(url) or 200)
        ha_client, ha_headers = device
        ha_client.put('/api/v2/device/webhook', json={'url': 'https://hooks.example.com/x'}, headers=ha_headers)
        bake = started(baker, loaf['id'], alert_mode='fancy')
        sent.clear()

        client, headers = as_panel(app, issue(device).json['token'])
        clock.advance(hours=1)
        client.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={'completed_at': at(1)}, headers=headers)
        assert sent == ['https://hooks.example.com/x']  # the HA showing the panel still needs to hear about it
