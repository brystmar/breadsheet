"""Tests for `flask --app main admins` (breadsheet#86)."""
from backend.admin_users import admins_command
from backend.database import db
from backend.models import Event, User
from backend.recipe_routes_v2_test import register
from pytest import fixture
from sqlalchemy import func, select


@fixture
def cli(app):
    def invoke(*args):
        return app.test_cli_runner().invoke(admins_command, list(args))
    return invoke


def admins(app) -> list[str]:
    with app.app_context():
        db.session.expire_all()
        return sorted(u.username for u in db.session.scalars(select(User).where(User.is_admin)))


def test_grant_list_and_revoke(app, client, cli):
    register(client, 'Bread-Head')
    register(app.test_client(), 'chief')
    result = cli('grant', 'bread_head', 'CHIEF')  # matched ignoring case, `-` and `_`
    assert result.exit_code == 0, result.output
    assert admins(app) == ['Bread-Head', 'chief']
    assert cli('list').output.split() == ['Bread-Head', 'chief']

    cli('revoke', 'chief')
    assert admins(app) == ['Bread-Head']


def test_an_unknown_name_changes_nothing(app, client, cli):
    register(client, 'chief')
    result = cli('grant', 'chief', 'nobody')
    assert result.exit_code != 0
    assert 'No such users: nobody. Nothing changed.' in result.output
    assert admins(app) == []


def test_create_a_reserved_name_as_an_admin(app, client, cli, tmp_path):
    keys = tmp_path / 'admin-key.txt'
    result = cli('create', 'admin', '--keys-file', str(keys), '--admin')
    assert result.exit_code == 0, result.output
    username, key = keys.read_text().split()
    assert username == 'admin' and key not in result.output
    assert keys.stat().st_mode & 0o777 == 0o600
    assert admins(app) == ['admin']

    signed_in = app.test_client().post('/api/v2/session', json={'key': key})
    assert signed_in.json['user'] == {**signed_in.json['user'], 'username': 'admin', 'is_admin': True}
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Event).where(Event.type == 'user_registered')) == 0


def test_create_refuses_taken_or_malformed_names_and_existing_files(app, client, cli, tmp_path):
    register(client, 'bread-head')
    assert 'is taken' in cli('create', 'Bread_Head', '--keys-file', str(tmp_path / 'a')).output
    assert cli('create', '9lives', '--keys-file', str(tmp_path / 'b')).exit_code != 0
    existing = tmp_path / 'c'
    existing.write_text('keep')
    assert cli('create', 'newbie', '--keys-file', str(existing)).exit_code != 0
    assert existing.read_text() == 'keep'
