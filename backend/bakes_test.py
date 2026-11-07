"""Tests for bakes (breadsheet#31): start, projection, check-off, cancel, auto-complete, time zones, idempotency."""
from backend.database import db
from backend.models import Bake
from backend.recipe_routes_v2_test import create, register
from datetime import datetime, timedelta, timezone
from pytest import fixture
from sqlalchemy import select

HOUR = 3600
# Saturday 2026-10-31, 9am in Los Angeles (PDT). Daylight saving ends Sunday at 2am.
NOW = datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc)
LA = 'America/Los_Angeles'

LOAF = {
    "name": "Weekend Loaf",
    "steps": [
        {"text": "Feed the levain", "note": "Levain must already be mature & active.",
         "then_wait": 7 * HOUR, "wait_min": 6 * HOUR, "wait_max": 8 * HOUR},
        {"text": "Mix", "wait_min": 1 * HOUR, "wait_max": 3 * HOUR, "active_seconds": 900, "needs_presence": True},
        {"text": "Bake", "then_wait": 0},
    ],
}


class Clock:
    def __init__(self):
        self.now = NOW

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr('backend.bake_routes.utc_now', lambda: clock.now)
    return clock


@fixture
def baker(client, clock):
    register(client, 'baker')
    return client


@fixture
def other(app, client):
    browser = app.test_client()
    register(browser, 'other')
    return browser


@fixture
def loaf(baker):
    return create(baker, LOAF).json['recipe']


def at(hours: float = 0, **kwargs) -> str:
    return (NOW + timedelta(hours=hours, **kwargs)).isoformat()


def start(client, recipe_id, headers=None, **fields):
    body = {"recipe_id": recipe_id, "anchor_type": "start", "anchor_time": at(1), "time_zone": LA, **fields}
    return client.post('/api/v2/bakes', json=body, headers=headers or {})


def started(client, recipe_id, **fields) -> dict:
    response = start(client, recipe_id, **fields)
    assert response.status_code == 201, response.json
    return response.json['bake']


def check_off(client, bake_id, position, when):
    return client.post(f'/api/v2/bakes/{bake_id}/steps/{position}/complete', json={"completed_at": when})


def skip(client, bake_id, position, when):
    return client.post(f'/api/v2/bakes/{bake_id}/steps/{position}/skip', json={"skipped_at": when})


def times(bake) -> list[str]:
    return [step['scheduled_at'] for step in bake['steps']]


def utc(hours: float) -> str:
    return (NOW + timedelta(hours=hours)).isoformat()


class TestStart:
    def test_snapshot_and_schedule(self, baker, loaf):
        bake = started(baker, loaf['id'])
        assert bake['name'] == 'Weekend Loaf' and bake['path'] == f"/bakes/{bake['suffix']}"
        assert bake['status'] == 'not_started' and bake['alert_mode'] == 'simple' and bake['created_via'] == 'web'
        assert bake['outcome'] is None and not any(step['skipped'] for step in bake['steps'])
        assert bake['recipe_id'] == loaf['id'] and bake['recipe_path'] == loaf['path'] and not bake['recipe_deleted']

        feed, mix, finish = bake['steps']
        assert (feed['text'], feed['note']) == ('Feed the levain', 'Levain must already be mature & active.')
        # The Then Wait, then the middle of a range with no Then Wait
        assert [s['wait_chosen'] for s in bake['steps']] == [7 * HOUR, 2 * HOUR, 0]
        assert times(bake) == [utc(1), utc(8), utc(10)]
        assert bake['projected_end'] == utc(10)
        assert mix['hands_on'] == {"seconds": 900, "estimated": False, "needs_presence": True}
        assert feed['hands_on'] == {"seconds": 600, "estimated": True, "needs_presence": True}  # unknown is not zero

    def test_a_finish_anchor_works_backward(self, baker, loaf):
        bake = started(baker, loaf['id'], anchor_type='finish', anchor_time=at(12))
        assert times(bake) == [utc(3), utc(10), utc(12)]
        assert bake['projected_end'] == utc(12)

    def test_local_times_follow_daylight_saving(self, baker, loaf):
        # 8pm PDT Saturday; the Mix step lands after clocks fall back at 2am Sunday
        bake = started(baker, loaf['id'], anchor_time='2026-10-31T20:00:00-07:00')
        assert [s['scheduled_at_local'] for s in bake['steps']] == [
            '2026-10-31T20:00:00-07:00', '2026-11-01T02:00:00-08:00', '2026-11-01T04:00:00-08:00']

    def test_waits_can_be_chosen_and_are_flagged_outside_the_range(self, baker, loaf):
        bake = started(baker, loaf['id'], waits=[{"position": 1, "wait_chosen": 9 * HOUR},
                                                 {"position": 2, "wait_chosen": 90 * 60}])
        assert [s['wait_chosen'] for s in bake['steps']] == [9 * HOUR, 90 * 60, 0]
        assert [s['wait_outside_range'] for s in bake['steps']] == [True, False, False]

    def test_recipe_edits_and_deletion_dont_touch_a_running_bake(self, baker, loaf):
        bake = started(baker, loaf['id'])
        baker.put(f"/api/v2/recipes/{loaf['id']}", json={**LOAF, "name": "Renamed", "steps": [{"text": "Just one"}]})
        assert baker.get(f"/api/v2/bakes/{bake['id']}").json['bake']['steps'] == bake['steps']

        baker.delete(f"/api/v2/recipes/{loaf['id']}", json={})
        after = baker.get(f"/api/v2/bakes/{bake['id']}").json['bake']
        assert (after['recipe_id'], after['recipe_path'], after['recipe_deleted']) == (None, None, True)
        assert after['name'] == 'Weekend Loaf' and len(after['steps']) == 3

    def test_any_visible_recipe_but_not_drafts(self, baker, other):
        theirs = create(other, LOAF).json['recipe']
        assert start(baker, theirs['id']).status_code == 201  # shared by link, no copy needed

        their_draft = create(other, {**LOAF, "is_draft": True}).json['recipe']
        assert start(baker, their_draft['id']).status_code == 404
        my_draft = create(baker, {**LOAF, "is_draft": True}).json['recipe']
        response = start(baker, my_draft['id'])
        assert (response.status_code, response.json['code']) == (409, 'recipe_is_draft')

        empty = create(baker, {**LOAF, "steps": []}).json['recipe']
        assert start(baker, empty['id']).json['code'] == 'recipe_has_no_steps'

    def test_validation(self, baker, loaf):
        response = start(baker, loaf['id'], anchor_type='middle', anchor_time='2026-11-01T08:00:00',
                         time_zone='Mars/Olympus_Mons', alert_mode='loud')
        assert response.status_code == 400 and response.json['code'] == 'bake_invalid'
        assert set(response.json['fields']) == {'anchor_type', 'anchor_time', 'time_zone', 'alert_mode'}
        assert start(baker, loaf['id'], waits=[{"position": 9, "wait_chosen": 60}]).json['fields'] == {
            'waits[0]': "Must name one of the recipe's step positions."}
        assert baker.post('/api/v2/bakes', json={"anchor_type": "start"}).json['fields'] == {'recipe_id': "Choose a recipe."}

    def test_waits_beyond_30_days(self, baker, loaf):
        response = start(baker, loaf['id'], waits=[{"position": 1, "wait_chosen": 31 * 24 * HOUR}])
        assert (response.status_code, response.json['code']) == (400, 'wait_out_of_range')

    def test_fancy_needs_home_assistant(self, baker, loaf):
        response = start(baker, loaf['id'], alert_mode='fancy')
        assert (response.status_code, response.json['code']) == (409, 'fancy_requires_ha')

    def test_a_schedule_already_over_is_refused(self, baker, loaf):
        response = start(baker, loaf['id'], anchor_type='finish', anchor_time=at(-1))
        assert (response.status_code, response.json['code']) == (400, 'bake_already_over')

    def test_signed_out(self, app, loaf):
        assert start(app.test_client(), loaf['id']).status_code == 401


class TestStartPartway:
    def test_earlier_steps_are_skipped(self, baker, loaf):
        bake = started(baker, loaf['id'], start_at_step=2)
        assert [s['skipped'] for s in bake['steps']] == [True, False, False]
        assert times(bake) == [None, utc(1), utc(3)]  # the anchor applies to step 2
        assert bake['status'] == 'in_progress' and bake['projected_end'] == utc(3)

    def test_a_finish_anchor_counts_only_the_remaining_steps(self, baker, loaf):
        bake = started(baker, loaf['id'], start_at_step=2, anchor_type='finish', anchor_time=at(5))
        assert times(bake) == [None, utc(3), utc(5)]

    def test_skipped_steps_count_as_done(self, baker, loaf, clock):
        bake = started(baker, loaf['id'], start_at_step=2)
        assert check_off(baker, bake['id'], 1, at(0)).json['bake'] == bake  # unchanged

        clock.advance(hours=3)
        for position, hours in ((2, 1), (3, 3)):
            after = check_off(baker, bake['id'], position, at(hours)).json['bake']
        assert after['outcome'] == 'finished'
        assert [s['completed_at'] for s in after['steps']] == [None, utc(1), utc(3)]

    def test_the_anchor_can_still_move_until_a_check_off(self, baker, loaf):
        bake = started(baker, loaf['id'], start_at_step=3)
        moved = baker.patch(f"/api/v2/bakes/{bake['id']}", json={"anchor_type": "start", "anchor_time": at(2)})
        assert times(moved.json['bake']) == [None, None, utc(2)]

    def test_the_step_must_exist(self, baker, loaf):
        for value in (0, 4, True, "2"):
            assert set(start(baker, loaf['id'], start_at_step=value).json['fields']) == {'start_at_step'}, value


class TestIdempotentStart:
    def test_a_repeat_returns_the_original_bake(self, app, baker, loaf):
        first = start(baker, loaf['id'], headers={'Idempotency-Key': 'tap-1'})
        again = start(baker, loaf['id'], headers={'Idempotency-Key': 'tap-1'}, anchor_time=at(5))
        assert (first.status_code, again.status_code) == (201, 200)
        assert again.json['bake']['id'] == first.json['bake']['id']
        with app.app_context():
            assert len(db.session.scalars(select(Bake)).all()) == 1

    def test_keys_are_per_user_and_bounded(self, baker, other, loaf):
        assert start(baker, loaf['id'], headers={'Idempotency-Key': 'same'}).status_code == 201
        assert start(other, loaf['id'], headers={'Idempotency-Key': 'same'}).status_code == 201
        assert start(baker, loaf['id'], headers={'Idempotency-Key': 'x' * 201}).json['code'] == 'idempotency_key_invalid'

    def test_a_repeat_skips_the_limit(self, baker, loaf):
        started(baker, loaf['id'])
        started(baker, loaf['id'])
        first = start(baker, loaf['id'], headers={'Idempotency-Key': 'third'})
        assert start(baker, loaf['id'], headers={'Idempotency-Key': 'third'}).json['bake']['id'] == first.json['bake']['id']


class TestLimit:
    def test_three_active_bakes(self, baker, loaf):
        bakes = [started(baker, loaf['id']) for _ in range(3)]
        response = start(baker, loaf['id'])
        assert (response.status_code, response.json['code']) == (409, 'bake_limit_reached')

        baker.post(f"/api/v2/bakes/{bakes[0]['id']}/cancel", json={})
        assert start(baker, loaf['id']).status_code == 201

    def test_expired_bakes_dont_count(self, baker, loaf, clock):
        for _ in range(3):
            started(baker, loaf['id'])
        clock.advance(hours=11)  # past every projected end
        assert start(baker, loaf['id'], anchor_time=(clock.now + timedelta(hours=1)).isoformat()).status_code == 201


class TestCheckOff:
    def test_early_check_off_re_projects_later_steps(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=1)
        after = check_off(baker, bake['id'], 1, at(1)).json['bake']
        assert after['status'] == 'in_progress'

        clock.advance(hours=5)
        after = check_off(baker, bake['id'], 2, at(6)).json['bake']  # mixed an hour early
        assert times(after) == [utc(1), utc(8), utc(8)]
        assert after['projected_end'] == utc(8)

    def test_out_of_order(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        after = check_off(baker, bake['id'], 2, at(2)).json['bake']
        assert after['steps'][0]['completed_at'] is None
        assert times(after) == [utc(1), utc(8), utc(4)]

    def test_the_first_write_wins(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=1)
        first = check_off(baker, bake['id'], 1, at(1)).json['bake']
        repeat = check_off(baker, bake['id'], 1, at(0.5))
        assert repeat.status_code == 200 and repeat.json['bake'] == first

    def test_completed_at_rules(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        for when in (at(minutes=6), at(-1), 'yesterday', '2026-10-31T16:00:00', None):
            response = check_off(baker, bake['id'], 1, when)
            assert (response.status_code, response.json['code']) == (400, 'completed_at_invalid'), when
        assert check_off(baker, bake['id'], 1, at(minutes=4)).status_code == 200  # five minutes of clock skew is fine
        assert check_off(baker, bake['id'], 9, at(0)).status_code == 404

    def test_checking_off_every_step_completes_the_bake(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=3)
        for position, hours in ((1, 1), (2, 2), (3, 3)):
            after = check_off(baker, bake['id'], position, at(hours)).json['bake']
        assert (after['status'], after['outcome'], after['completed_at']) == ('completed', 'finished', utc(3))
        assert baker.get('/api/v2/bakes').json['bakes'] == []


class TestSkip:
    """Skipping a step mid-bake (breadsheet#78). The loaf: feed (7h), mix (2h), bake, starting at hour 1."""

    def test_skipping_drops_the_wait_and_re_projects(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        check_off(baker, bake['id'], 1, at(1))
        after = skip(baker, bake['id'], 2, at(2)).json['bake']

        mix = after['steps'][1]
        assert (mix['skipped'], mix['skipped_at'], mix['completed_at']) == (True, utc(2), None)
        assert mix['skipped_at_local'] == '2026-10-31T11:00:00-07:00'
        assert times(after) == [utc(1), None, utc(8)]  # the bake follows the feed's 7 hours; mix's 2 drop out
        assert after['projected_end'] == utc(8) and after['status'] == 'in_progress'

    def test_skipping_doesnt_start_a_bake(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(minutes=30)
        after = skip(baker, bake['id'], 2, at(0.5)).json['bake']
        assert after['status'] == 'not_started'
        assert times(after) == [utc(1), None, utc(8)]

        clock.advance(hours=1)
        assert check_off(baker, bake['id'], 1, at(1)).json['bake']['status'] == 'in_progress'

    def test_a_finish_anchor_keeps_its_finish_until_a_check_off(self, baker, loaf, clock):
        bake = started(baker, loaf['id'], anchor_type='finish', anchor_time=at(12))
        clock.advance(minutes=30)
        after = skip(baker, bake['id'], 2, at(0.5)).json['bake']
        assert times(after) == [utc(5), None, utc(12)]  # the start moves later; the finish stays put

    def test_the_first_write_wins(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        first = skip(baker, bake['id'], 2, at(1.5)).json['bake']
        repeat = skip(baker, bake['id'], 2, at(2))
        assert repeat.status_code == 200 and repeat.json['bake'] == first

        checked = check_off(baker, bake['id'], 1, at(1)).json['bake']
        assert skip(baker, bake['id'], 1, at(2)).json['bake'] == checked  # already checked off: unchanged
        assert check_off(baker, bake['id'], 2, at(2)).json['bake'] == checked  # already skipped: unchanged

    def test_skipped_at_rules(self, baker, other, loaf, clock):
        bake = started(baker, loaf['id'])
        for when in (at(minutes=6), at(-1), 'yesterday', '2026-10-31T16:00:00', None):
            response = skip(baker, bake['id'], 2, when)
            assert (response.status_code, response.json['code']) == (400, 'skipped_at_invalid'), when
        assert skip(baker, bake['id'], 9, at(0)).status_code == 404
        assert skip(other, bake['id'], 2, at(0)).status_code == 404
        assert skip(baker, bake['id'], 2, at(minutes=4)).status_code == 200  # five minutes of clock skew is fine

        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        response = skip(baker, bake['id'], 3, at(minutes=4))
        assert (response.status_code, response.json['code']) == (409, 'bake_completed')

    def test_skipping_the_last_steps_finishes_the_bake(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=3)
        check_off(baker, bake['id'], 1, at(1))
        skip(baker, bake['id'], 2, at(2))
        after = skip(baker, bake['id'], 3, at(2.5)).json['bake']
        assert (after['status'], after['outcome'], after['completed_at']) == ('completed', 'finished', utc(2.5))

    def test_complete_leaves_skipped_steps_skipped(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        check_off(baker, bake['id'], 1, at(1))
        skip(baker, bake['id'], 2, at(1.5))
        done = baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={}).json['bake']
        assert [s['skipped'] for s in done['steps']] == [False, True, False]
        assert [s['completed_at'] for s in done['steps']] == [utc(1), None, utc(2)]

    def test_steps_skipped_at_start_have_no_skip_time(self, baker, loaf):
        bake = started(baker, loaf['id'], start_at_step=2)
        assert [(s['skipped'], s['skipped_at']) for s in bake['steps']] == [(True, None), (False, None), (False, None)]


class TestCompletion:
    def test_expires_an_hour_after_the_projected_end(self, app, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=10, minutes=59)  # projected end was at 10 hours: still in the grace hour
        assert baker.get(f"/api/v2/bakes/{bake['id']}").json['bake']['status'] == 'not_started'

        clock.advance(minutes=1)
        after = baker.get(f"/api/v2/bakes/{bake['id']}").json['bake']
        assert (after['status'], after['outcome'], after['completed_at']) == ('completed', 'expired', utc(11))
        with app.app_context():  # written back on read
            assert db.session.scalar(select(Bake.outcome)) == 'expired'

    def test_late_check_offs_count_during_the_grace_hour(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=10, minutes=30)
        for position in (1, 2, 3):
            after = check_off(baker, bake['id'], position, clock.now.isoformat()).json['bake']
        assert after['outcome'] == 'finished'

    def test_cancel_leaves_steps_unchecked(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        check_off(baker, bake['id'], 1, at(1))
        canceled = baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={}).json['bake']
        assert (canceled['status'], canceled['outcome'], canceled['completed_at']) == ('completed', 'canceled', utc(2))
        assert [s['completed_at'] for s in canceled['steps']] == [utc(1), None, None]

        clock.advance(hours=1)
        again = baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={}).json['bake']
        assert again['completed_at'] == utc(2)

    def test_complete_checks_off_the_rest(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=2)
        check_off(baker, bake['id'], 1, at(1))
        done = baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={}).json['bake']  # completed_at: now
        assert (done['status'], done['outcome'], done['completed_at']) == ('completed', 'finished', utc(2))
        assert [s['completed_at'] for s in done['steps']] == [utc(1), utc(2), utc(2)]

        clock.advance(hours=1)
        again = baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={"completed_at": at(3)})
        assert again.status_code == 200 and again.json['bake'] == done
        assert baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={}).json['bake']['outcome'] == 'finished'

    def test_complete_at_a_given_time(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=3)
        assert baker.post(f"/api/v2/bakes/{bake['id']}/complete",
                          json={"completed_at": at(hours=3, minutes=6)}).json['code'] == 'completed_at_invalid'
        done = baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={"completed_at": at(2.5)}).json['bake']
        assert done['completed_at'] == utc(2.5)

    def test_a_canceled_bake_cant_be_completed(self, baker, loaf):
        bake = started(baker, loaf['id'])
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})
        response = baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={})
        assert (response.status_code, response.json['code']) == (409, 'bake_completed')

    def test_a_finished_bake_takes_no_more_input(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=1)
        check_off(baker, bake['id'], 1, at(1))
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})

        assert check_off(baker, bake['id'], 1, at(0.5)).status_code == 200  # already done: unchanged
        response = check_off(baker, bake['id'], 2, at(1))
        assert (response.status_code, response.json['code']) == (409, 'bake_completed')
        assert baker.patch(f"/api/v2/bakes/{bake['id']}", json={"alert_mode": "simple"}).json['code'] == 'bake_completed'


class TestChange:
    def test_waits_re_project(self, baker, loaf):
        bake = started(baker, loaf['id'])
        after = baker.patch(f"/api/v2/bakes/{bake['id']}", json={"waits": [{"position": 1, "wait_chosen": 6 * HOUR}]})
        assert times(after.json['bake']) == [utc(1), utc(7), utc(9)]

    def test_the_anchor_moves_only_before_the_first_check_off(self, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        moved = baker.patch(f"/api/v2/bakes/{bake['id']}", json={"anchor_type": "finish", "anchor_time": at(20)})
        assert moved.json['bake']['projected_end'] == utc(20)

        clock.advance(hours=11)
        check_off(baker, bake['id'], 1, (clock.now).isoformat())
        response = baker.patch(f"/api/v2/bakes/{bake['id']}", json={"anchor_type": "start", "anchor_time": at(12)})
        assert (response.status_code, response.json['code']) == (409, 'bake_in_progress')

    def test_alert_mode_and_empty_changes(self, baker, loaf):
        bake = started(baker, loaf['id'])
        assert baker.patch(f"/api/v2/bakes/{bake['id']}", json={"alert_mode": "fancy"}).json['code'] == 'fancy_requires_ha'
        assert baker.patch(f"/api/v2/bakes/{bake['id']}", json={}).json['code'] == 'body_invalid'


class TestAccess:
    def test_bakes_are_private(self, app, baker, other, loaf):
        bake = started(baker, loaf['id'])
        for method, path, body in (('get', f"/api/v2/bakes/{bake['id']}", None),
                                   ('get', f"/api/v2/bakes/by-suffix/{bake['suffix']}", None),
                                   ('patch', f"/api/v2/bakes/{bake['id']}", {"alert_mode": "simple"}),
                                   ('post', f"/api/v2/bakes/{bake['id']}/cancel", {}),
                                   ('post', f"/api/v2/bakes/{bake['id']}/steps/1/complete", {"completed_at": at(0)})):
            assert getattr(other, method)(path, json=body).status_code == 404, path
        assert other.get('/api/v2/bakes').json['bakes'] == []
        assert app.test_client().get('/api/v2/bakes').status_code == 401

    def test_owner_resolves_a_bake_url(self, baker, loaf):
        bake = started(baker, loaf['id'])
        assert baker.get(f"/api/v2/bakes/by-suffix/{bake['suffix']}").json['bake']['id'] == bake['id']
        assert baker.get('/api/v2/bakes/by-suffix/nope').status_code == 404

    def test_active_and_completed_lists(self, baker, loaf):
        first, second = started(baker, loaf['id']), started(baker, loaf['id'])
        baker.post(f"/api/v2/bakes/{first['id']}/cancel", json={})
        assert [b['id'] for b in baker.get('/api/v2/bakes').json['bakes']] == [second['id']]
        assert [b['id'] for b in baker.get('/api/v2/bakes?status=completed').json['bakes']] == [first['id']]
        assert baker.get('/api/v2/bakes?status=everything').json['code'] == 'status_invalid'
