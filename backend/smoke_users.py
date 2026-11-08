"""
Test users for manual and smoke testing: `flask --app main test-users`.

Test usernames start with `test-dev-` or `test-prod-`, so they're easy to spot. Signup refuses the `test-`
prefix (backend/identity.py), so only this command makes them, and it skips the signup rate limit and
records no events. The usage metrics leave test users out (backend/metrics.py).

Keys are shown once: `create` writes them to a new file (readable only by you) instead of printing them.
Move them into the password manager and delete the file. Never put them in `.env`, docs, or fixtures.
"""
import click
from backend.database import db
from backend.identity import TEST_USERNAME_PREFIX, generate_key, hash_key
from backend.models import Bake, Event, Recipe, User
from flask.cli import with_appcontext
from os import O_CREAT, O_EXCL, O_WRONLY, fdopen, open as os_open
from pathlib import Path
from re import fullmatch
from sqlalchemy import delete, func, select

ENVIRONMENTS = ('dev', 'prod')
MAX_PER_RUN = 50


def prefix_for(environment: str) -> str:
    return f"{TEST_USERNAME_PREFIX}{environment}-"


def is_test_username(username: str) -> bool:
    return username.lower().startswith(TEST_USERNAME_PREFIX)


def find_test_users(environment: str | None = None) -> list[User]:
    """Every test user, or only one environment's, by username."""
    prefix = prefix_for(environment) if environment else TEST_USERNAME_PREFIX
    return list(db.session.scalars(select(User).where(func.lower(User.username).startswith(prefix))
                                   .order_by(func.lower(User.username))))


def next_numbers(environment: str, count: int) -> list[int]:
    """The next `count` numbers after the highest existing test-<env>-NN user."""
    prefix = prefix_for(environment)
    taken = [int(match.group(1)) for user in find_test_users(environment)
             if (match := fullmatch(rf"{prefix}(\d+)", user.username.lower()))]
    start = max(taken, default=0) + 1
    return list(range(start, start + count))


def create_test_users(environment: str, count: int) -> list[tuple[User, str]]:
    """Creates `count` test users and returns each with its key. Commits."""
    created = []
    for number in next_numbers(environment, count):
        key = generate_key()
        user = User(username=f"{prefix_for(environment)}{number:02d}", key_hash=hash_key(key))
        db.session.add(user)
        created.append((user, key))
    db.session.commit()
    return created


def delete_test_user(user: User) -> dict[str, int]:
    """Deletes a test user and everything they made, including their events. Doesn't commit."""
    if not is_test_username(user.username):
        raise ValueError(f"{user.username} isn't a test user")

    counts = {}
    for name, statement in (
            ('events', delete(Event).where(Event.user_id == user.id)),
            ('bakes', delete(Bake).where(Bake.user_id == user.id)),         # cascades to bake steps
            ('recipes', delete(Recipe).where(Recipe.owner_id == user.id)),  # cascades to steps and prerequisites
    ):
        counts[name] = db.session.execute(statement).rowcount
    db.session.delete(user)
    return counts


def write_keys(path: Path, created: list[tuple[User, str]]):
    """Writes `username key` lines to a new file only the owner can read; refuses to overwrite."""
    with fdopen(os_open(path, O_WRONLY | O_CREAT | O_EXCL, 0o600), 'w') as file:
        for user, key in created:
            file.write(f"{user.username} {key}\n")


@click.group('test-users')
def users_command():
    """Create, list, and delete test users (test-dev-NN, test-prod-NN)."""


@users_command.command('create')
@click.option('--env', 'environment', type=click.Choice(ENVIRONMENTS), required=True,
              help="Which prefix to use. Point DATABASE_URL at the matching database.")
@click.option('--count', type=click.IntRange(1, MAX_PER_RUN), default=5, show_default=True)
@click.option('--keys-file', type=click.Path(dir_okay=False, writable=True, path_type=Path), required=True,
              help="A new file for the keys (never overwritten). Keep it out of the repo.")
@click.option('--yes', is_flag=True, help="Don't ask for confirmation.")
@with_appcontext
def create_command(environment, count, keys_file, yes):
    """Create test users; their keys go to --keys-file, never the terminal."""
    if keys_file.exists():
        raise click.BadParameter(f"{keys_file} already exists", param_hint='--keys-file')
    names = [f"{prefix_for(environment)}{number:02d}" for number in next_numbers(environment, count)]
    if not yes:
        click.confirm(f"Create {', '.join(names)}?", abort=True)

    created = create_test_users(environment, count)
    write_keys(keys_file, created)
    click.echo(f"Created {len(created)} test users. Keys are in {keys_file}: move them to the password "
               f"manager, then delete the file.")


@users_command.command('list')
@click.option('--env', 'environment', type=click.Choice(ENVIRONMENTS))
@with_appcontext
def list_command(environment):
    """List test users with how much each has made."""
    users = find_test_users(environment)
    if not users:
        click.echo("No test users.")
    for user in users:
        recipes = db.session.scalar(select(func.count()).select_from(Recipe).where(Recipe.owner_id == user.id))
        bakes = db.session.scalar(select(func.count()).select_from(Bake).where(Bake.user_id == user.id))
        click.echo(f"{user.username}  created {user.created_at:%Y-%m-%d}  recipes={recipes} bakes={bakes}")


@users_command.command('delete')
@click.argument('usernames', nargs=-1, required=True)
@click.option('--yes', is_flag=True, help="Don't ask for confirmation.")
@with_appcontext
def delete_command(usernames, yes):
    """Delete test users and everything they made. Refuses any username without the test- prefix."""
    not_test = [name for name in usernames if not is_test_username(name)]
    if not_test:
        raise click.BadParameter(f"not test users: {', '.join(not_test)}", param_hint='USERNAMES')

    users = list(db.session.scalars(select(User).where(func.lower(User.username).in_([n.lower() for n in usernames]))))
    missing = sorted(set(n.lower() for n in usernames) - {user.username.lower() for user in users})
    if missing:
        raise click.ClickException(f"No such users: {', '.join(missing)}")
    if not yes:
        click.confirm(f"Permanently delete {', '.join(u.username for u in users)} and their recipes, bakes, "
                      f"and events?", abort=True)

    for user in users:
        counts = delete_test_user(user)
        click.echo(f"Deleted {user.username}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    db.session.commit()
