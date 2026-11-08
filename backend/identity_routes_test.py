"""Tests for signup and sessions (/api/v2/users, /api/v2/session), against the local test Postgres."""
from backend.database import db
from backend.identity import hash_key
from backend.models import User, utc_now
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from unittest.mock import patch
from uuid import UUID

COOKIE = 'breadsheet_session'


def signup(client, username='Thomas_B', **kwargs):
    return client.post('/api/v2/users', json={'username': username}, **kwargs)


def sign_in(client, key):
    return client.post('/api/v2/session', json={'key': key})


def stored_user() -> User:
    db.session.expire_all()
    return db.session.scalar(select(User))


def set_cookie_header(response) -> str:
    return next(v for k, v in response.headers.items() if k == 'Set-Cookie' and v.startswith(COOKIE))


class TestSignup:
    def test_creates_user_returns_key_once_and_signs_in(self, client):
        response = signup(client)
        assert response.status_code == 201
        assert response.headers['Cache-Control'] == 'no-store'

        user, key = response.json['user'], response.json['key']
        assert UUID(user['id']).version == 7
        assert user['username'] == 'Thomas_B'
        assert len(key) == 22

        # This browser is now signed in
        assert client.get('/api/v2/session').json == {'user': user}

        # Only the key's hash is stored
        stored = db.session.scalar(select(User))
        assert stored.key_hash == hash_key(key)

    def test_session_cookie_attributes(self, client):
        header = set_cookie_header(signup(client))
        assert 'HttpOnly' in header
        assert 'SameSite=Lax' in header
        assert 'Expires=' in header  # permanent: one year, refreshed on use
        assert 'Domain=' not in header  # host-only on the API host

    def test_username_is_trimmed_and_keeps_its_case(self, client):
        assert signup(client, '  BreadHead  ').json['user']['username'] == 'BreadHead'

    def test_username_taken_ignores_case(self, client):
        signup(client, 'BreadHead')
        response = signup(client, 'breadhead')
        assert response.status_code == 409
        assert response.json['code'] == 'username_taken'

    def test_hyphens_and_underscores_count_as_the_same(self, client):
        signup(client, 'bread-head')
        response = signup(app_client(client), 'Bread_Head')
        assert response.status_code == 409
        assert response.json['code'] == 'username_taken'

    def test_invalid_username(self, client):
        response = signup(client, 'no spaces')
        assert response.status_code == 400
        assert response.json['code'] == 'username_invalid'
        assert 'letters, numbers' in response.json['message']

    def test_reserved_username(self, client):
        response = signup(client, 'Admin')
        assert response.status_code == 400
        assert 'reserved' in response.json['message']

    def test_body_must_be_a_json_object(self, client):
        response = client.post('/api/v2/users', json=['Thomas_B'])
        assert response.status_code == 400
        assert response.json['code'] == 'body_invalid'

    def test_requires_json_content_type(self, client):
        # Forces a CORS preflight, which (with SameSite=Lax) is the CSRF protection
        response = client.post('/api/v2/users', data='{"username": "Thomas_B"}', content_type='text/plain')
        assert response.status_code == 415
        assert response.json['code'] == 'json_required'
        assert db.session.scalar(select(User)) is None

    def test_rate_limit_five_per_hour(self, client):
        for i in range(5):
            assert signup(client, f'baker{i}').status_code == 201
        response = signup(client, 'baker5')
        assert response.status_code == 429
        assert response.json['code'] == 'rate_limited'
        assert 0 < int(response.headers['Retry-After']) <= 3600

    def test_failed_signups_dont_count(self, client):
        for _ in range(6):
            signup(client, 'x')
        assert signup(client, 'baker').status_code == 201


class TestSignIn:
    def test_key_signs_in_another_browser(self, app, client):
        user = signup(client).json

        phone = app.test_client()  # a second browser
        response = sign_in(phone, user['key'])
        assert response.status_code == 200
        assert response.json == {'user': user['user']}
        assert phone.get('/api/v2/session').json == {'user': user['user']}

    def test_surrounding_whitespace_is_ignored(self, app, client):
        key = signup(client).json['key']
        phone = app.test_client()  # a second browser
        assert sign_in(phone, f'  {key}\n').status_code == 200

    def test_wrong_key(self, app, client):
        signup(client)
        phone = app.test_client()  # a second browser
        response = sign_in(phone, 'x' * 22)
        assert response.status_code == 401
        assert response.json['code'] == 'key_invalid'
        assert phone.get('/api/v2/session').status_code == 401

    def test_malformed_keys(self, client):
        for key in [None, 42, '', 'short', 'x' * 500, ['a' * 22]]:
            assert sign_in(client, key).status_code == 401

    def test_rate_limit_ten_failures(self, app, client):
        key = signup(client).json['key']
        attacker = app.test_client()  # a second browser
        for _ in range(10):
            assert sign_in(attacker, 'x' * 22).status_code == 401

        # Blocked even with the right key until the window ends
        response = sign_in(attacker, key)
        assert response.status_code == 429
        assert response.json['code'] == 'rate_limited'
        assert 0 < int(response.headers['Retry-After']) <= 15 * 60

    def test_successful_sign_ins_dont_count(self, app, client):
        key = signup(client).json['key']
        phone = app.test_client()  # a second browser
        for _ in range(12):
            assert sign_in(phone, key).status_code == 200


class TestSession:
    def test_not_signed_in(self, client):
        response = client.get('/api/v2/session')
        assert response.status_code == 401
        assert response.json['code'] == 'not_signed_in'

    def test_sign_out_only_affects_this_browser(self, app, client):
        key = signup(client).json['key']
        phone = app.test_client()  # a second browser
        sign_in(phone, key)

        response = client.delete('/api/v2/session', json={})
        assert response.status_code == 204
        assert client.get('/api/v2/session').status_code == 401
        assert phone.get('/api/v2/session').status_code == 200

    def test_sign_out_requires_json(self, client):
        signup(client)
        assert client.delete('/api/v2/session').status_code == 415
        assert client.get('/api/v2/session').status_code == 200

    def test_session_ends_when_key_changes(self, client):
        signup(client)
        user = db.session.scalar(select(User))
        user.key_hash = hash_key('a-new-key-from-a-future-reset')
        db.session.commit()

        response = client.get('/api/v2/session')
        assert response.status_code == 401
        assert client.get_cookie(COOKIE) is None  # the stale cookie is cleared

    def test_session_for_deleted_user(self, client):
        signup(client)
        db.session.execute(db.delete(User))
        db.session.commit()
        assert client.get('/api/v2/session').status_code == 401

    def test_tampered_cookie(self, client):
        signup(client)
        client.set_cookie(COOKIE, 'forged.value.signature')
        assert client.get('/api/v2/session').status_code == 401

    def test_last_seen_updates_at_most_daily(self, client):
        signup(client)
        user = db.session.scalar(select(User))
        recently = utc_now() - timedelta(hours=1)
        user.last_seen_at = recently
        db.session.commit()

        client.get('/api/v2/session')
        assert stored_user().last_seen_at == recently

        user = stored_user()
        user.last_seen_at = utc_now() - timedelta(days=2)
        db.session.commit()
        client.get('/api/v2/session')
        assert utc_now() - stored_user().last_seen_at < timedelta(minutes=1)

    def test_anonymous_requests_get_no_cookie(self, client):
        assert 'Set-Cookie' not in client.get('/api/v1/recipes').headers
        assert 'Set-Cookie' not in client.get('/api/v2/session').headers


class TestV2Conventions:
    def test_unknown_path_returns_json_404(self, client):
        response = client.get('/api/v2/nope')
        assert response.status_code == 404
        assert response.json['code'] == 'not_found'

    def test_wrong_method_returns_json_405(self, client):
        response = client.put('/api/v2/session', json={})
        assert response.status_code == 405
        assert response.json['code'] == 'method_not_allowed'
        assert 'GET' in response.headers['Allow']

    def test_database_outage_returns_503(self, client):
        outage = OperationalError('SELECT 1', None, Exception('connection refused'))
        with patch('backend.identity_routes.current_user', side_effect=outage):
            response = client.get('/api/v2/session')
        assert response.status_code == 503
        assert response.json['code'] == 'service_unavailable'
        assert response.headers['Retry-After'] == '30'

    def test_v1_404s_are_unchanged(self, client):
        assert client.get('/api/v1/recipe/not-a-uuid').status_code == 404

    def test_credentialed_cors_preflight(self, client):
        response = client.options('/api/v2/session', headers={
            'Origin':                         'https://breadsheet.com',
            'Access-Control-Request-Method':  'POST',
            'Access-Control-Request-Headers': 'Content-Type'})
        assert response.headers['Access-Control-Allow-Origin'] == 'https://breadsheet.com'
        assert response.headers['Access-Control-Allow-Credentials'] == 'true'

        response = client.options('/api/v2/session', headers={
            'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'})
        assert 'Access-Control-Allow-Origin' not in response.headers


class TestNothingSecretIsLogged:
    def test_keys_never_appear_in_logs(self, app, client, caplog):
        import logging
        caplog.set_level(logging.DEBUG)

        key = signup(client).json['key']
        phone = app.test_client()
        sign_in(phone, key)
        sign_in(phone, 'y' * 22)  # a failed attempt
        phone.get('/api/v2/session')

        assert key not in caplog.text
        assert 'y' * 22 not in caplog.text


def app_client(client):
    """A second browser, so a signup doesn't reuse the first one's session."""
    return client.application.test_client()


def check(client, username):
    return client.get(f'/api/v2/usernames/{username}')


class TestUsernameCheck:
    """GET /api/v2/usernames/<username> (breadsheet#83)"""

    def test_available(self, client):
        response = check(client, 'Bread_Head')
        assert response.status_code == 200
        assert response.json == {'username': 'Bread_Head', 'available': True}
        assert response.headers['Cache-Control'].startswith('no-store')

    def test_taken_ignoring_case_and_separators(self, client):
        signup(client, 'bread-head')
        response = check(app_client(client), 'BREAD_HEAD')
        assert response.json == {'username': 'BREAD_HEAD', 'available': False, 'code': 'username_taken',
                                 'message': "That username is taken. Please pick another."}

    def test_gives_the_same_answer_as_signup(self, client):
        for name in ['ab', '9lives', 'Support', 'test-dev-07', 'bread-sheet-team', 'fuckbread', 'has%20space']:
            checked = check(client, name).json
            assert checked['available'] is False
            signed_up = signup(app_client(client), checked['username'])
            assert signed_up.status_code == 400
            assert (checked['code'], checked['message']) == (signed_up.json['code'], signed_up.json['message'])

    def test_needs_no_session_and_creates_nothing(self, client):
        response = check(client, 'newbaker')
        assert 'Set-Cookie' not in response.headers
        assert db.session.scalar(select(User)) is None

    def test_rate_limit_sixty_a_minute(self, client):
        for i in range(60):
            assert check(client, f'baker{i}').status_code == 200
        response = check(client, 'baker60')
        assert response.status_code == 429
        assert response.json['code'] == 'rate_limited'
        assert 0 < int(response.headers['Retry-After']) <= 60
