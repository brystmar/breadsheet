"""Tests for webhook nudges to Home Assistant (breadsheet#93)."""
import logging
from backend import nudges
from backend.bakes_test import at, baker, clock, loaf, other, start, started  # noqa: F401 (fixtures)
from backend.connections_test import as_device, paired_token
from backend.database import db
from backend.models import Connection
from pytest import fixture, mark
from sqlalchemy import select

HOOK = 'https://hooks.example.com/api/webhook/abc123'
OTHER_HOOK = 'https://ha.example.net/api/webhook/def456'
PUBLIC = '93.184.216.34'


@fixture
def sent(monkeypatch):
    """Nudges sent, by URL, with public DNS and a 200 from every webhook unless a test says otherwise."""
    class Sent(list):
        statuses: dict
    calls = Sent()
    statuses = {}
    monkeypatch.setattr(nudges, 'resolve', lambda host: [PUBLIC])
    monkeypatch.setattr(nudges, 'run_in_background', lambda work: work())  # inline, so tests see the result

    def send(url, address):
        assert address == PUBLIC  # always the address that was checked
        calls.append(url)
        return statuses.get(url, 200)
    monkeypatch.setattr(nudges, 'send', send)
    calls.statuses = statuses
    return calls


def paired(app, baker, url=None):
    """A Home Assistant paired with the baker, with its webhook set if `url` is given."""
    client, headers = as_device(app, paired_token(app, baker))
    if url:
        response = client.put('/api/v2/device/webhook', json={'url': url}, headers=headers)
        assert response.status_code == 204, response.json
    return client, headers


def stored_urls(app):
    with app.app_context():
        return [c.webhook_url for c in db.session.scalars(select(Connection).order_by(Connection.created_at))]


class TestRegistering:
    def test_home_assistant_sets_and_clears_its_webhook(self, app, baker, sent):
        client, headers = paired(app, baker, HOOK)
        assert stored_urls(app) == [HOOK]
        assert client.delete('/api/v2/device/webhook', json={}, headers=headers).status_code == 204
        assert stored_urls(app) == [None]

    def test_the_url_is_never_returned(self, app, baker, sent):
        paired(app, baker, HOOK)
        assert HOOK not in baker.get('/api/v2/connections').get_data(as_text=True)

    def test_browsers_cant_set_one(self, baker, sent):
        response = baker.put('/api/v2/device/webhook', json={'url': HOOK})
        assert (response.status_code, response.json['code']) == (403, 'scope_missing')

    @mark.parametrize('url', [
        'http://hooks.example.com/api/webhook/abc', 'https://hooks.example.com:8443/hook',
        'https://user:pass@hooks.example.com/hook', 'https:///no-host', 'ftp://hooks.example.com/x',
        'https://hooks.example.com/' + 'x' * 2000, '', None, 42,
    ])
    def test_only_plain_https_urls(self, app, baker, sent, url):
        client, headers = paired(app, baker)
        response = client.put('/api/v2/device/webhook', json={'url': url}, headers=headers)
        assert (response.status_code, response.json['code']) == (400, 'webhook_url_invalid')

    @mark.parametrize('addresses', [['127.0.0.1'], ['10.0.0.5'], ['192.168.1.20'], ['169.254.169.254'],
                                    ['::1'], ['fd00::1'], [PUBLIC, '10.0.0.5'], []])
    def test_only_public_addresses(self, app, baker, sent, monkeypatch, addresses):
        monkeypatch.setattr(nudges, 'resolve', lambda host: addresses)
        client, headers = paired(app, baker)
        response = client.put('/api/v2/device/webhook', json={'url': HOOK}, headers=headers)
        assert response.json['code'] == 'webhook_url_invalid'

    def test_names_that_dont_resolve_are_refused(self, app, baker, sent, monkeypatch):
        def fail(host):
            raise OSError("no such host")
        monkeypatch.setattr(nudges, 'resolve', fail)
        client, headers = paired(app, baker)
        assert client.put('/api/v2/device/webhook', json={'url': HOOK},
                          headers=headers).json['code'] == 'webhook_url_invalid'

    def test_revoking_clears_it(self, app, baker, sent):
        paired(app, baker, HOOK)
        connection = baker.get('/api/v2/connections').json['connections'][0]
        baker.delete(f"/api/v2/connections/{connection['id']}", json={})
        assert stored_urls(app) == [None]


class TestNudging:
    def test_starting_a_fancy_bake_nudges(self, app, baker, loaf, sent):
        paired(app, baker, HOOK)
        started(baker, loaf['id'], alert_mode='fancy')
        assert sent == [HOOK]

    def test_simple_bakes_dont(self, app, baker, loaf, sent, clock):
        paired(app, baker, HOOK)
        bake = started(baker, loaf['id'])
        clock.advance(hours=1)
        baker.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={'completed_at': at(1)})
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        assert sent == []

    def test_every_change_to_a_fancy_bake_nudges(self, app, baker, loaf, sent, clock):
        paired(app, baker, HOOK)
        bake = started(baker, loaf['id'], alert_mode='fancy')
        bake_url = f"/api/v2/bakes/{bake['id']}"
        clock.advance(hours=1)
        baker.post(f"{bake_url}/steps/1/complete", json={'completed_at': at(1)})
        baker.post(f"{bake_url}/steps/2/skip", json={'skipped_at': at(1)})
        baker.patch(bake_url, json={'waits': [{'position': 3, 'wait_chosen': 60}]})
        baker.post(f"{bake_url}/complete", json={})
        assert len(sent) == 5

    def test_repeats_that_change_nothing_dont(self, app, baker, loaf, sent, clock):
        paired(app, baker, HOOK)
        bake = started(baker, loaf['id'], alert_mode='fancy')
        clock.advance(hours=1)
        baker.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={'completed_at': at(1)})
        baker.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={'completed_at': at(1)})
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        assert len(sent) == 3  # start, check-off, cancel

    def test_switching_to_and_from_fancy_nudges(self, app, baker, loaf, sent):
        paired(app, baker, HOOK)
        bake = started(baker, loaf['id'])
        baker.patch(f"/api/v2/bakes/{bake['id']}", json={'alert_mode': 'fancy'})
        baker.patch(f"/api/v2/bakes/{bake['id']}", json={'alert_mode': 'simple'})
        assert len(sent) == 2

    def test_the_calling_home_assistant_isnt_nudged(self, app, baker, loaf, sent):
        client, headers = paired(app, baker, HOOK)
        paired(app, baker, OTHER_HOOK)
        response = start(client, loaf['id'], headers=headers, alert_mode='fancy')
        assert response.status_code == 201
        assert sent == [OTHER_HOOK]

    def test_other_users_home_assistants_arent_nudged(self, app, baker, other, loaf, sent):
        paired(app, other, OTHER_HOOK)
        paired(app, baker, HOOK)
        started(baker, loaf['id'], alert_mode='fancy')
        assert sent == [HOOK]

    def test_a_gone_webhook_is_cleared(self, app, baker, loaf, sent):
        paired(app, baker, HOOK)
        sent.statuses[HOOK] = 410
        started(baker, loaf['id'], alert_mode='fancy')
        assert stored_urls(app) == [None]

    def test_a_failing_webhook_never_fails_the_change(self, app, baker, loaf, sent, caplog):
        paired(app, baker, HOOK)
        sent.statuses[HOOK] = None  # timed out
        started(baker, loaf['id'], alert_mode='fancy')
        assert stored_urls(app) == [HOOK]
        assert HOOK not in caplog.text  # never logged

    def test_an_exception_while_nudging_never_fails_the_change(self, app, baker, loaf, sent, monkeypatch, caplog):
        paired(app, baker, HOOK)

        def broken(url, address):
            raise RuntimeError("boom")
        monkeypatch.setattr(nudges, 'send', broken)
        with caplog.at_level(logging.ERROR):
            response = start(baker, loaf['id'], alert_mode='fancy')
        assert response.status_code == 201
        assert 'Nudging connection' in caplog.text
        assert HOOK not in caplog.text

    def test_a_failure_before_sending_never_fails_the_change(self, app, baker, loaf, sent, monkeypatch, caplog):
        paired(app, baker, HOOK)

        def broken(work):
            raise RuntimeError("no threads")
        monkeypatch.setattr(nudges, 'run_in_background', broken)
        with caplog.at_level(logging.ERROR):
            response = start(baker, loaf['id'], alert_mode='fancy')
        assert response.status_code == 201
        assert 'Nudging Home Assistant failed' in caplog.text

    def test_a_host_that_turned_private_isnt_called(self, app, baker, loaf, sent, monkeypatch):
        paired(app, baker, HOOK)
        monkeypatch.setattr(nudges, 'resolve', lambda host: ['10.0.0.5'])  # DNS changed since registering
        started(baker, loaf['id'], alert_mode='fancy')
        assert sent == []


class FakeResponse:
    def __init__(self, status):
        self.status = status


def test_the_sender_connects_to_the_checked_address_and_doesnt_follow_redirects(monkeypatch):
    """The real sender, with the socket layer replaced."""
    seen = {}

    def connect(self):
        seen['address'], seen['host'] = self._address, self.host
    monkeypatch.setattr(nudges.PinnedConnection, 'connect', connect)
    monkeypatch.setattr(nudges.PinnedConnection, 'request',
                        lambda self, method, path, body, headers: seen.update(method=method, path=path, body=body))
    monkeypatch.setattr(nudges.PinnedConnection, 'getresponse', lambda self: FakeResponse(302))

    assert nudges.send(HOOK + '?x=1', PUBLIC) == 302  # a redirect is just a status; nothing follows it
    assert seen == {'method': 'POST', 'path': '/api/webhook/abc123?x=1', 'body': b'{}'}


def test_the_pinned_connection_dials_the_address_not_the_name(monkeypatch):
    dialed = {}

    def create_connection(target, timeout):
        dialed['target'] = target
        raise OSError("stop here")
    monkeypatch.setattr(nudges.socket, 'create_connection', create_connection)
    assert nudges.send(HOOK, PUBLIC) is None  # unreachable: nothing sent, no exception
    assert dialed['target'] == (PUBLIC, 443)


def test_background_work_runs_on_a_thread():
    from threading import Event
    done = Event()
    nudges.run_in_background(done.set)
    assert done.wait(2)
