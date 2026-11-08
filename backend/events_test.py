"""Tests for product events and usage metrics (breadsheet#34)."""
from backend.bakes_test import LOAF, at, baker, check_off, clock, loaf, other, skip, started  # noqa: F401 (fixtures)
from backend.database import db
from backend.events import agent_name
from backend.metrics import METRICS, metrics_command, run_metrics
from backend.models import Event, User
from backend.recipe_routes_v2_test import create, register
from sqlalchemy import select


def recorded(app, event_type=None) -> list[Event]:
    with app.app_context():
        query = select(Event).order_by(Event.id)
        if event_type:
            query = query.where(Event.type == event_type)
        found = list(db.session.scalars(query))
        db.session.expunge_all()
        return found


def types(app) -> list[str]:
    return [event.type for event in recorded(app)]


class TestIdentityEvents:
    def test_signing_up_and_in(self, app, client):
        user = register(client, 'newbie')
        assert types(app) == ['user_registered']
        event = recorded(app)[0]
        assert str(event.user_id) == user['id']
        assert (event.client, event.agent_name, event.recipe_id, event.bake_id, event.value) == ('web', None, None, None, None)

    def test_signing_in_with_a_key(self, app, client):
        signup = client.post('/api/v2/users', json={'username': 'keyholder'}).json
        browser = app.test_client()
        assert browser.post('/api/v2/session', json={'key': signup['key']}).status_code == 200
        assert types(app) == ['user_registered', 'signed_in']


class TestRecipeEvents:
    def test_create_copy_publish_unpublish_delete(self, app, baker, other):
        recipe = create(baker).json['recipe']
        copy = other.post(f"/api/v2/recipes/{recipe['id']}/copy", json={}).json['recipe']
        assert baker.post(f"/api/v2/recipes/{recipe['id']}/publish", json={}).status_code == 200
        assert baker.post(f"/api/v2/recipes/{recipe['id']}/publish", json={}).status_code == 200  # again: no new event
        assert baker.delete(f"/api/v2/recipes/{recipe['id']}/publish", json={}).status_code == 204
        assert baker.delete(f"/api/v2/recipes/{recipe['id']}/publish", json={}).status_code == 204  # again: no new event
        assert other.delete(f"/api/v2/recipes/{copy['id']}", json={}).status_code == 204

        recipe_events = [event for event in recorded(app) if event.type.startswith('recipe_')]
        assert [event.type for event in recipe_events] == [
            'recipe_created', 'recipe_copied', 'recipe_published', 'recipe_unpublished', 'recipe_deleted']
        # A copy records what was copied; a delete keeps the id of what's gone
        assert str(recipe_events[1].recipe_id) == recipe['id']
        assert str(recipe_events[4].recipe_id) == copy['id']


class TestBakeEvents:
    def test_start_check_off_skip_and_cancel(self, app, baker, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=1, minutes=10)
        assert check_off(baker, bake['id'], 1, at(1, minutes=10)).status_code == 200
        assert check_off(baker, bake['id'], 1, at(1, minutes=11)).status_code == 200  # first write wins: no event
        assert skip(baker, bake['id'], 2, at(1, minutes=10)).status_code == 200
        assert baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={}).status_code == 200

        bake_events = [event for event in recorded(app) if event.bake_id is not None]
        assert [event.type for event in bake_events] == ['bake_started', 'step_completed', 'step_skipped', 'bake_canceled']
        assert {str(event.bake_id) for event in bake_events} == {bake['id']}
        assert {str(event.recipe_id) for event in bake_events} == {loaf['id']}
        # Ten minutes after step 1's scheduled time
        assert bake_events[1].value == 600

    def test_an_early_check_off_is_negative(self, app, baker, loaf, clock):
        bake = started(baker, loaf['id'], anchor_time=at(0, minutes=3))
        assert check_off(baker, bake['id'], 1, at(0)).status_code == 200
        assert recorded(app, 'step_completed')[0].value == -180

    def test_complete_records_once(self, app, baker, loaf, clock):
        bake = started(baker, loaf['id'], anchor_time=at(0))
        assert baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={}).status_code == 200
        assert baker.post(f"/api/v2/bakes/{bake['id']}/complete", json={}).status_code == 200
        assert len(recorded(app, 'bake_completed')) == 1

    def test_a_repeated_idempotency_key_records_one_start(self, app, baker, loaf):
        headers = {'Idempotency-Key': 'same-key'}
        for _ in range(2):
            baker.post('/api/v2/bakes', headers=headers, json={"recipe_id": loaf['id'], "anchor_type": "start",
                                                               "anchor_time": at(1), "time_zone": 'America/Los_Angeles'})
        assert len(recorded(app, 'bake_started')) == 1


class TestAgentAttribution:
    def test_agent_calls_are_marked_with_a_cleaned_name(self, app, baker, loaf):
        headers = {'X-Breadsheet-Via': 'agent', 'X-Breadsheet-Agent': 'Claude <script>alert(1)</script> Opus'}
        baker.post('/api/v2/bakes', headers=headers, json={"recipe_id": loaf['id'], "anchor_type": "start",
                                                           "anchor_time": at(1), "time_zone": 'America/Los_Angeles'})
        event = recorded(app, 'bake_started')[0]
        assert event.client == 'agent'
        assert event.agent_name == 'Claude scriptalert1script Opus'

    def test_agent_names_are_short_plain_labels(self):
        assert agent_name('  ') is None
        assert agent_name(None) is None
        assert agent_name('x' * 100) == 'x' * 40
        assert agent_name('Home Assistant Assist 2026.11') == 'Home Assistant Assist 2026.11'


class TestBrowserEvents:
    def test_records_an_ics_export_for_your_bake(self, app, baker, loaf):
        bake = started(baker, loaf['id'])
        response = baker.post('/api/v2/events', json={'type': 'ics_exported', 'bake_id': bake['id']})
        assert response.status_code == 204
        event = recorded(app, 'ics_exported')[0]
        assert (str(event.bake_id), str(event.recipe_id)) == (bake['id'], loaf['id'])

    def test_refuses_types_off_the_allow_list(self, app, baker, loaf):
        bake = started(baker, loaf['id'])
        for event_type in ('bake_started', 'anything', None):
            response = baker.post('/api/v2/events', json={'type': event_type, 'bake_id': bake['id']})
            assert response.status_code == 400
            assert response.json['code'] == 'event_type_invalid'
        assert recorded(app, 'bake_started')[0].bake_id is not None
        assert len(recorded(app, 'bake_started')) == 1

    def test_only_for_your_own_bakes_and_signed_in(self, app, baker, other, loaf):
        bake = started(baker, loaf['id'])
        assert other.post('/api/v2/events', json={'type': 'ics_exported', 'bake_id': bake['id']}).status_code == 404
        assert other.post('/api/v2/events', json={'type': 'ics_exported'}).status_code == 400
        assert app.test_client().post('/api/v2/events', json={'type': 'ics_exported', 'bake_id': bake['id']}).status_code == 401
        assert recorded(app, 'ics_exported') == []


class TestDeletion:
    def test_deleting_a_user_keeps_their_events_without_the_id(self, app, client):
        user = register(client, 'leaving')
        with app.app_context():
            db.session.delete(db.session.get(User, user['id']))
            db.session.commit()
        events = recorded(app)
        assert [event.type for event in events] == ['user_registered']
        assert events[0].user_id is None


class TestMetrics:
    def test_every_metric_runs_and_counts(self, app, baker, other, loaf, clock):
        bake = started(baker, loaf['id'])
        clock.advance(hours=1, minutes=10)
        check_off(baker, bake['id'], 1, at(1, minutes=10))   # late
        check_off(baker, bake['id'], 2, at(1, minutes=10))   # early (it was due hours later)
        baker.post('/api/v2/events', json={'type': 'ics_exported', 'bake_id': bake['id']})
        baker.post(f"/api/v2/bakes/{bake['id']}/cancel", json={})      # step 3 never checked off
        other.post(f"/api/v2/recipes/{loaf['id']}/copy", json={})

        with app.app_context():
            results = run_metrics(db.session)
        assert set(results) == {name for name, _, _ in METRICS}
        assert results['bakes_started_vs_finished'] == [{'started': 1, 'finished': 0, 'canceled': 1, 'expired': 0, 'still_going': 0}]
        assert results['step_check_offs'] == [{'on_time': 1, 'late': 1, 'never': 1}]
        assert results['alert_modes_and_exports'] == [{'alert_mode': 'simple', 'bakes': 1, 'exported': 1}]
        assert results['most_copied'] == [{'recipe': LOAF['name'], 'kind': 'personal', 'copies': 1}]
        assert results['weekly_active_bakers'][0]['bakers'] == 1
        assert results['returning_bakers'] == [{'bakers': 1, 'returned': 0}]

    def test_the_command_prints_each_metric(self, app, client):
        output = app.test_cli_runner().invoke(metrics_command)
        assert output.exit_code == 0, output.output
        for name, question, _ in METRICS:
            assert f"{name}: {question}" in output.output
