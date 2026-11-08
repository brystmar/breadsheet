"""Tests for test users and `flask --app main test-users`."""
from backend.bakes_test import LOAF, check_off, at, clock, started  # noqa: F401 (fixtures)
from backend.database import db
from backend.metrics import run_metrics
from backend.models import Bake, Event, Recipe, User
from backend.recipe_routes_v2_test import create, register
from backend.smoke_users import create_test_users, find_test_users, users_command
from pytest import fixture
from sqlalchemy import func, select


def count(model) -> int:
    return db.session.scalar(select(func.count()).select_from(model))


@fixture
def cli(app):
    def invoke(*args, **kwargs):
        return app.test_cli_runner().invoke(users_command, list(args), **kwargs)
    return invoke


class TestCreate:
    def test_numbers_continue_after_the_highest(self, app, client):
        with app.app_context():
            create_test_users('dev', 2)
            create_test_users('dev', 1)
            create_test_users('prod', 1)
            assert [u.username for u in find_test_users('dev')] == ['test-dev-01', 'test-dev-02', 'test-dev-03']
            assert [u.username for u in find_test_users()] == ['test-dev-01', 'test-dev-02', 'test-dev-03',
                                                               'test-prod-01']
            assert count(Event) == 0  # no user_registered events

    def test_keys_go_to_a_private_file_and_sign_in(self, app, client, cli, tmp_path):
        keys_file = tmp_path / 'keys.txt'
        result = cli('create', '--env', 'dev', '--count', '2', '--keys-file', str(keys_file), '--yes')
        assert result.exit_code == 0, result.output

        lines = keys_file.read_text().splitlines()
        assert [line.split()[0] for line in lines] == ['test-dev-01', 'test-dev-02']
        assert keys_file.stat().st_mode & 0o777 == 0o600
        key = lines[0].split()[1]
        assert key not in result.output

        response = app.test_client().post('/api/v2/session', json={'key': key})
        assert response.status_code == 200
        assert response.json['user']['username'] == 'test-dev-01'

    def test_never_overwrites_a_keys_file(self, app, client, cli, tmp_path):
        keys_file = tmp_path / 'keys.txt'
        keys_file.write_text('keep me')
        result = cli('create', '--env', 'prod', '--keys-file', str(keys_file), '--yes')
        assert result.exit_code != 0
        assert keys_file.read_text() == 'keep me'
        with app.app_context():
            assert find_test_users() == []

    def test_asks_first(self, app, client, cli, tmp_path):
        result = cli('create', '--env', 'dev', '--count', '1', '--keys-file', str(tmp_path / 'k'), input='n\n')
        assert result.exit_code != 0
        assert 'test-dev-01' in result.output
        with app.app_context():
            assert find_test_users() == []


class TestDelete:
    def test_deletes_the_user_and_everything_they_made(self, app, client, clock, cli, tmp_path):
        keys_file = tmp_path / 'keys.txt'
        cli('create', '--env', 'dev', '--count', '1', '--keys-file', str(keys_file), '--yes')
        browser = app.test_client()
        browser.post('/api/v2/session', json={'key': keys_file.read_text().split()[1]})
        loaf = create(browser, LOAF).json['recipe']
        started(browser, loaf['id'])

        result = cli('delete', 'TEST-DEV-01', '--yes')
        assert result.exit_code == 0, result.output
        with app.app_context():
            assert (count(User), count(Recipe), count(Bake), count(Event)) == (0, 0, 0, 0)

    def test_refuses_real_users(self, app, client, cli):
        register(client, 'realbaker')
        result = cli('delete', 'realbaker', '--yes')
        assert result.exit_code != 0
        assert 'not test users' in result.output
        with app.app_context():
            assert count(User) == 1

    def test_unknown_names(self, app, client, cli):
        result = cli('delete', 'test-dev-99', '--yes')
        assert result.exit_code != 0
        assert 'No such users: test-dev-99' in result.output


def test_list(app, client, cli):
    assert 'No test users.' in cli('list').output
    with app.app_context():
        create_test_users('prod', 1)
    output = cli('list', '--env', 'prod').output
    assert 'test-prod-01' in output and 'recipes=0 bakes=0' in output


def test_signup_refuses_the_prefix(client):
    response = client.post('/api/v2/users', json={'username': 'Test-Prod-01'})
    assert response.status_code == 400
    assert 'reserved' in response.json['message'].lower()


def test_metrics_leave_test_users_out(app, client, clock, cli, tmp_path):
    keys_file = tmp_path / 'keys.txt'
    cli('create', '--env', 'prod', '--count', '1', '--keys-file', str(keys_file), '--yes')
    tester = app.test_client()
    tester.post('/api/v2/session', json={'key': keys_file.read_text().split()[1]})
    loaf = create(tester, LOAF).json['recipe']
    bake = started(tester, loaf['id'])
    clock.advance(hours=1, minutes=10)
    check_off(tester, bake['id'], 1, at(1, minutes=10))

    register(client, 'realbaker')
    client.post(f"/api/v2/recipes/{loaf['id']}/copy", json={})  # a real user's copy still counts

    with app.app_context():
        results = run_metrics(db.session)
    assert results['bakes_started_vs_finished'][0]['started'] == 0
    assert results['step_check_offs'] == [{'on_time': 0, 'late': 0, 'never': 0}]
    assert results['weekly_active_bakers'] == []
    assert results['returning_bakers'] == [{'bakers': 0, 'returned': 0}]
    assert results['waits_outside_range'] == [{'outside': 0, 'steps': 0}]
    assert results['most_copied'][0]['copies'] == 1
    assert results['detailed_recipes'] == [{'detail_level': 'simple', 'recipes': 1}]  # only the real user's copy
