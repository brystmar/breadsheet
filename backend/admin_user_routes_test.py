"""Tests for the admin users and metrics endpoints (breadsheet#87)."""
from backend.admin_routes_test import make_admin
from backend.bakes_test import LOAF, clock, started  # noqa: F401 (fixtures)
from backend.database import db
from backend.metrics import METRICS
from backend.models import Event, User
from backend.recipe_routes_v2_test import create, register
from backend.smoke_users import create_test_users
from datetime import timedelta
from pytest import fixture
from sqlalchemy import select


@fixture
def admin(app, client):
    """The test client, signed in as the admin `chief`."""
    register(client, 'chief')
    make_admin(app, 'chief')
    return client


def browser(app, username):
    """Another browser, signed up as `username`; returns (client, user dict, key)."""
    other = app.test_client()
    response = other.post('/api/v2/users', json={'username': username})
    return other, response.json['user'], response.json['key']


def listed(admin, query=''):
    return admin.get(f'/api/v2/admin/users{query}').json['users']


class TestUsersList:
    def test_newest_first_with_counts(self, app, admin, clock, monkeypatch):
        monkeypatch.setattr('backend.admin_user_routes.utc_now', lambda: clock.now)  # the bake's clock
        baker, _, _ = browser(app, 'baker')
        loaf = create(baker, LOAF).json['recipe']
        baker.post(f"/api/v2/recipes/{loaf['id']}/publish", json={})
        started(baker, loaf['id'])

        users = listed(admin)
        assert [u['username'] for u in users] == ['baker', 'chief']
        assert {k: users[0][k] for k in ('recipe_count', 'published_count', 'bake_count', 'active_bake_count',
                                         'is_admin', 'is_test', 'is_active')} == {
            'recipe_count': 1, 'published_count': 1, 'bake_count': 1, 'active_bake_count': 1,
            'is_admin': False, 'is_test': False, 'is_active': True}
        assert users[1]['is_admin'] is True
        assert 'last_seen_at' in users[0] and 'key_hash' not in users[0]

    def test_filters(self, app, admin):
        browser(app, 'bread-head')
        with app.app_context():
            create_test_users('dev', 1)
            old = db.session.scalar(select(User).where(User.username == 'bread-head'))
            old.last_seen_at -= timedelta(days=45)
            db.session.commit()

        assert [u['username'] for u in listed(admin, '?q=BREAD_he')] == ['bread-head']
        assert 'test-dev-01' not in [u['username'] for u in listed(admin, '?tests=0')]
        assert [u['is_test'] for u in listed(admin) if u['username'] == 'test-dev-01'] == [True]
        assert [u['username'] for u in listed(admin, '?active=1')] == ['test-dev-01', 'chief']

    def test_admins_only(self, app, client):
        assert app.test_client().get('/api/v2/admin/users').json['code'] == 'not_signed_in'
        register(client, 'baker')
        assert client.get('/api/v2/admin/users').json['code'] == 'admin_required'


class TestKeyReset:
    def test_new_key_works_and_the_old_one_and_sessions_stop(self, app, admin):
        baker, user, old_key = browser(app, 'baker')
        assert baker.get('/api/v2/session').status_code == 200

        response = admin.post(f"/api/v2/admin/users/{user['id']}/key", json={})
        assert response.status_code == 200
        new_key = response.json['key']
        assert response.json['user']['username'] == 'baker' and new_key != old_key

        assert baker.get('/api/v2/session').status_code == 401  # signed out everywhere
        assert app.test_client().post('/api/v2/session', json={'key': old_key}).status_code == 401
        assert app.test_client().post('/api/v2/session', json={'key': new_key}).json['user']['username'] == 'baker'
        with app.app_context():
            assert [str(e.user_id) for e in db.session.scalars(select(Event).where(Event.type == 'key_reset'))] == [user['id']]

    def test_not_your_own(self, app, admin):
        me = admin.get('/api/v2/session').json['user']
        response = admin.post(f"/api/v2/admin/users/{me['id']}/key", json={})
        assert (response.status_code, response.json['code']) == (403, 'own_key_reset')
        assert admin.get('/api/v2/session').status_code == 200

    def test_unknown_users(self, admin):
        for user_id in ('nope', '0193a1b2-0000-7000-8000-000000000000'):
            assert admin.post(f'/api/v2/admin/users/{user_id}/key', json={}).status_code == 404


class TestRename:
    def rename(self, admin, user_id, username):
        return admin.patch(f'/api/v2/admin/users/{user_id}', json={'username': username})

    def test_rename_shows_everywhere(self, app, admin):
        baker, user, _ = browser(app, 'baker')
        loaf = create(baker, LOAF).json['recipe']
        response = self.rename(admin, user['id'], 'Master-Baker')
        assert response.json['user']['username'] == 'Master-Baker'
        assert baker.get('/api/v2/session').json['user']['username'] == 'Master-Baker'  # still signed in
        assert baker.get(f"/api/v2/recipes/{loaf['id']}").json['recipe']['owner'] == 'Master-Baker'

    def test_reserved_names_are_allowed_but_the_rest_of_the_rules_apply(self, app, admin):
        _, user, _ = browser(app, 'baker')
        browser(app, 'bread-head')
        assert self.rename(admin, user['id'], 'support').status_code == 200
        assert self.rename(admin, user['id'], 'Bread_Head').json['code'] == 'username_taken'
        assert self.rename(admin, user['id'], '9lives').json['code'] == 'username_invalid'
        assert self.rename(admin, user['id'], 'fuckbread').json['code'] == 'username_invalid'
        assert self.rename(admin, user['id'], 'Support').status_code == 200  # case change of their own name

    def test_body_and_unknown_users(self, app, admin):
        _, user, _ = browser(app, 'baker')
        assert admin.patch(f"/api/v2/admin/users/{user['id']}", json=['x']).json['code'] == 'body_invalid'
        assert self.rename(admin, 'nope', 'whoever').status_code == 404


def test_metrics(app, admin, clock):
    baker, _, _ = browser(app, 'baker')
    started(baker, create(baker, LOAF).json['recipe']['id'])

    response = admin.get('/api/v2/admin/metrics')
    assert response.status_code == 200
    metrics = {m['name']: m for m in response.json['metrics']}
    assert list(metrics) == [name for name, _, _ in METRICS]
    assert metrics['bakes_started_vs_finished']['rows'][0]['started'] == 1
    assert metrics['bakes_started_vs_finished']['columns'] == ['started', 'finished', 'canceled', 'expired', 'still_going']
    assert metrics['agents']['columns'] == ['bakes_started_by_agents', 'recipes_imported']
    week = metrics['weekly_active_bakers']['rows'][0]['week']
    assert len(week) == 10 and week[4] == '-'   # ISO date
    assert app.test_client().get('/api/v2/admin/metrics').status_code == 401
