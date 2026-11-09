"""Tests for Fancy alerts with Home Assistant, the alert filter, and cheap idle polls (breadsheet#33)."""
from backend import poll_cache
from backend.bakes_test import at, baker, clock, loaf, other, start, started  # noqa: F401 (fixtures)
from backend.cache import cache
from backend.connections_test import as_device, issue_code, pair, paired_token
from backend.database import db
from contextlib import contextmanager
from pytest import fixture
from sqlalchemy import event
from uuid import uuid4

POLL = '/api/v2/bakes?status=active&alert=fancy'


@fixture
def device(app, baker):
    """Home Assistant, paired with the baker's account."""
    client, headers = as_device(app, paired_token(app, baker))

    def poll(**extra_headers):
        return client.get(POLL, headers={**headers, **extra_headers})
    poll.client, poll.headers = client, headers
    return poll


@contextmanager
def counted_queries(app):
    """Counts the SQL statements run inside the block."""
    statements = []
    with app.app_context():
        engine = db.engine

    def count(conn, cursor, statement, *args):
        statements.append(statement)
    event.listen(engine, 'before_cursor_execute', count)
    try:
        yield statements
    finally:
        event.remove(engine, 'before_cursor_execute', count)


class TestFancyNeedsAPairing:
    def test_fancy_works_once_home_assistant_is_paired(self, device, baker, loaf):
        bake = started(baker, loaf['id'], alert_mode='fancy')
        assert bake['alert_mode'] == 'fancy'

    def test_switching_to_fancy_works_once_paired(self, device, baker, loaf):
        bake = started(baker, loaf['id'])
        response = baker.patch(f"/api/v2/bakes/{bake['id']}", json={"alert_mode": "fancy"})
        assert response.json['bake']['alert_mode'] == 'fancy'

    def test_home_assistant_can_start_a_fancy_bake(self, device, loaf):
        response = start(device.client, loaf['id'], headers=device.headers, alert_mode='fancy')
        assert response.status_code == 201, response.json
        assert response.json['bake']['created_via'] == 'ha'

    def test_a_revoked_pairing_doesnt_count(self, app, baker, loaf):
        pair(app, issue_code(baker))
        connection = baker.get('/api/v2/connections').json['connections'][0]
        baker.delete(f"/api/v2/connections/{connection['id']}", json={})
        response = start(baker, loaf['id'], alert_mode='fancy')
        assert (response.status_code, response.json['code']) == (409, 'fancy_requires_ha')

    def test_someone_elses_pairing_doesnt_count(self, app, other, baker, loaf):
        pair(app, issue_code(other))
        assert start(baker, loaf['id'], alert_mode='fancy').json['code'] == 'fancy_requires_ha'


class TestAlertFilter:
    def test_alert_keeps_one_mode(self, device, baker, loaf):
        simple = started(baker, loaf['id'])
        fancy = started(baker, loaf['id'], alert_mode='fancy')
        assert [b['id'] for b in baker.get('/api/v2/bakes?alert=fancy').json['bakes']] == [fancy['id']]
        assert [b['id'] for b in baker.get('/api/v2/bakes?alert=simple').json['bakes']] == [simple['id']]
        assert len(baker.get('/api/v2/bakes').json['bakes']) == 2

    def test_alert_filters_completed_bakes_too(self, device, baker, loaf):
        fancy = started(baker, loaf['id'], alert_mode='fancy')
        baker.post(f"/api/v2/bakes/{fancy['id']}/cancel", json={})
        assert baker.get('/api/v2/bakes?status=completed&alert=simple').json['bakes'] == []
        assert len(baker.get('/api/v2/bakes?status=completed&alert=fancy').json['bakes']) == 1

    def test_an_unknown_alert_is_refused(self, baker):
        response = baker.get('/api/v2/bakes?alert=loud')
        assert (response.status_code, response.json['code']) == (400, 'alert_invalid')


class TestEtagsAndPollInterval:
    def test_the_interval_is_a_minute_while_a_fancy_bake_is_active(self, device, baker, loaf):
        assert device().headers['X-Breadsheet-Poll-Interval'] == '120'
        started(baker, loaf['id'], alert_mode='fancy')
        assert device().headers['X-Breadsheet-Poll-Interval'] == '60'

    def test_simple_bakes_dont_speed_up_polling(self, device, baker, loaf):
        started(baker, loaf['id'])
        assert device().headers['X-Breadsheet-Poll-Interval'] == '120'

    def test_completed_lists_have_no_interval(self, baker):
        assert 'X-Breadsheet-Poll-Interval' not in baker.get('/api/v2/bakes?status=completed').headers

    def test_an_unchanged_list_is_a_304(self, device, baker, loaf):
        started(baker, loaf['id'], alert_mode='fancy')
        first = device()
        etag = first.headers['ETag']
        again = device(**{'If-None-Match': etag})
        assert again.status_code == 304
        assert again.data == b''
        assert again.headers['X-Breadsheet-Poll-Interval'] == '60'
        assert again.headers['Cache-Control'] == 'no-store'

    def test_a_change_gets_a_new_etag(self, device, baker, loaf, clock):
        bake = started(baker, loaf['id'], alert_mode='fancy')
        etag = device().headers['ETag']
        clock.advance(hours=1)
        assert baker.post(f"/api/v2/bakes/{bake['id']}/steps/1/complete", json={"completed_at": at(1)}).status_code == 200
        changed = device(**{'If-None-Match': etag})
        assert changed.status_code == 200
        assert changed.json['bakes'][0]['steps'][0]['completed_at'] is not None

    def test_idle_answers_from_the_cache_match_the_databases(self, app, device):
        from_database = device()
        with counted_queries(app) as statements:
            from_cache = device()
        assert statements == []
        assert (from_cache.json, from_cache.headers['ETag']) == (from_database.json, from_database.headers['ETag'])
        assert device(**{'If-None-Match': from_database.headers['ETag']}).status_code == 304


class TestIdlePolls:
    def test_idle_polls_never_touch_the_database(self, app, device):
        assert device().json == {'bakes': []}  # checks the token and finds no Fancy bakes
        with counted_queries(app) as statements:
            for _ in range(3):
                response = device()
                assert (response.status_code, response.json) == (200, {'bakes': []})
        assert statements == []

    def test_a_new_fancy_bake_shows_up_on_the_next_poll(self, device, baker, loaf):
        device()
        bake = started(baker, loaf['id'], alert_mode='fancy')
        assert [b['id'] for b in device().json['bakes']] == [bake['id']]

    def test_switching_a_bake_to_fancy_shows_up_on_the_next_poll(self, device, baker, loaf):
        bake = started(baker, loaf['id'])
        assert device().json['bakes'] == []
        baker.patch(f"/api/v2/bakes/{bake['id']}", json={"alert_mode": "fancy"})
        assert [b['id'] for b in device().json['bakes']] == [bake['id']]

    def test_polls_with_a_fancy_bake_use_the_database(self, app, device, baker, loaf):
        started(baker, loaf['id'], alert_mode='fancy')
        device()
        with counted_queries(app) as statements:
            assert len(device().json['bakes']) == 1
        assert statements

    def test_a_fancy_bake_ending_lets_polls_go_idle_again(self, app, device, baker, loaf):
        bake = started(baker, loaf['id'], alert_mode='fancy')
        assert len(device().json['bakes']) == 1
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        assert device().json['bakes'] == []
        with counted_queries(app) as statements:
            device()
        assert statements == []

    def test_revoking_stops_the_token_at_once(self, device, baker):
        device()
        connection = baker.get('/api/v2/connections').json['connections'][0]
        baker.delete(f"/api/v2/connections/{connection['id']}", json={})
        response = device()
        assert (response.status_code, response.json['code']) == (401, 'token_invalid')

    def test_an_empty_cache_falls_back_to_the_database(self, device, baker, loaf):
        device()
        cache.clear()  # memcache evicts whenever it likes
        assert device().json == {'bakes': []}
        bake = started(baker, loaf['id'], alert_mode='fancy')
        cache.clear()
        assert [b['id'] for b in device().json['bakes']] == [bake['id']]

    def test_unknown_tokens_are_still_refused(self, app, device):
        device()
        client, headers = as_device(app, 'not-a-real-token')
        response = client.get(POLL, headers=headers)
        assert response.status_code == 401, (response.status_code, response.get_data(as_text=True)[:200])
        assert response.json['code'] == 'token_invalid'

    def test_other_lists_always_use_the_database(self, app, device):
        device()
        with counted_queries(app) as statements:
            device.client.get('/api/v2/bakes?status=active', headers=device.headers)
        assert statements

    def test_browsers_always_use_the_database(self, app, device, baker):
        device()
        with counted_queries(app) as statements:
            assert baker.get(POLL).json == {'bakes': []}
        assert statements


class TestFancyGenerations:
    def test_a_note_from_before_a_fancy_change_is_ignored(self):
        user_id = uuid4()
        generation = poll_cache.fancy_generation(user_id)  # read before the database query...
        poll_cache.fancy_changed(user_id)                  # ...a Fancy bake starts meanwhile...
        poll_cache.note_no_fancy(user_id, generation)      # ...and the stale answer comes back
        assert not poll_cache.has_no_fancy(user_id)

    def test_a_current_note_is_believed(self):
        user_id = uuid4()
        poll_cache.note_no_fancy(user_id, poll_cache.fancy_generation(user_id))
        assert poll_cache.has_no_fancy(user_id)

    def test_a_lost_generation_makes_notes_stale(self):
        user_id = uuid4()
        poll_cache.note_no_fancy(user_id, poll_cache.fancy_generation(user_id))
        cache.delete(f'fgen:{user_id}')
        assert not poll_cache.has_no_fancy(user_id)
        poll_cache.fancy_generation(user_id)  # a new one starts
        assert not poll_cache.has_no_fancy(user_id)

    def test_no_cache_means_no_note(self):
        user_id = uuid4()
        poll_cache.note_no_fancy(user_id, None)
        assert not poll_cache.has_no_fancy(user_id)
