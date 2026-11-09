"""
Admins (breadsheet#86): `flask --app main admins grant|revoke|list|create`.

Admin is a flag on users, set only here, never through the API, so nobody can make themselves an admin from
the website. Run it like a migration: point DATABASE_URL at the database for that one command.
`create` makes a user directly (reserved names allowed, no signup event or rate limit) and writes the key to a
new file only you can read, never the terminal.
"""
import click
from backend.database import db
from backend.identity import USERNAME_PATTERN, generate_key, hash_key, normalized_username_column, username_taken
from backend.models import User, normalized_username
from backend.smoke_users import write_keys
from flask.cli import with_appcontext
from pathlib import Path
from re import fullmatch
from sqlalchemy import select


def find_users(usernames) -> tuple[list[User], list[str]]:
    """The users with these names (ignoring case, `-` and `_`), and the names that matched nobody."""
    wanted = {normalized_username(name): name for name in usernames}
    found = list(db.session.scalars(select(User).where(normalized_username_column().in_(wanted))))
    missing = sorted(set(wanted) - {normalized_username(user.username) for user in found})
    return found, [wanted[name] for name in missing]


def set_admin(usernames, value: bool) -> list[User]:
    """Grants or revokes admin for every name, or changes nothing if any name is unknown."""
    users, missing = find_users(usernames)
    if missing:
        raise click.ClickException(f"No such users: {', '.join(missing)}. Nothing changed.")
    for user in users:
        user.is_admin = value
    db.session.commit()
    return users


@click.group('admins')
def admins_command():
    """Grant, revoke, and list admins; create users signup refuses."""


@admins_command.command('grant')
@click.argument('usernames', nargs=-1, required=True)
@with_appcontext
def grant_command(usernames):
    """Make these users admins."""
    for user in set_admin(usernames, True):
        click.echo(f"{user.username} is an admin")


@admins_command.command('revoke')
@click.argument('usernames', nargs=-1, required=True)
@with_appcontext
def revoke_command(usernames):
    """Stop these users being admins."""
    for user in set_admin(usernames, False):
        click.echo(f"{user.username} is no longer an admin")


@admins_command.command('list')
@with_appcontext
def list_command():
    """Every admin."""
    admins = list(db.session.scalars(select(User).where(User.is_admin).order_by(User.username)))
    click.echo("\n".join(user.username for user in admins) if admins else "No admins.")


@admins_command.command('create')
@click.argument('username')
@click.option('--keys-file', type=click.Path(dir_okay=False, writable=True, path_type=Path), required=True,
              help="A new file for the key (never overwritten). Keep it out of the repo.")
@click.option('--admin', 'make_admin', is_flag=True, help="Also make the new user an admin.")
@with_appcontext
def create_command(username, keys_file, make_admin):
    """Create a user directly, even with a reserved name; the key goes to --keys-file, never the terminal."""
    if keys_file.exists():
        raise click.BadParameter(f"{keys_file} already exists", param_hint='--keys-file')
    if not fullmatch(USERNAME_PATTERN, username):
        raise click.BadParameter("3 to 30 letters, numbers, underscores, and hyphens, starting with a letter",
                                 param_hint='USERNAME')
    if username_taken(username):
        raise click.ClickException(f"{username} is taken (ignoring case, `-` and `_`).")

    key = generate_key()
    user = User(username=username, key_hash=hash_key(key), is_admin=make_admin)
    db.session.add(user)
    db.session.commit()
    write_keys(keys_file, [(user, key)])
    click.echo(f"Created {username}{' (admin)' if make_admin else ''}. The key is in {keys_file}: move it to "
               f"the password manager, then delete the file.")
