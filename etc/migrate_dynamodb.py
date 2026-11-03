"""
One-time migration of recipes and replacements from DynamoDB to Postgres (Second Rise item 4).

Reads production DynamoDB (us-west-1) and loads every recipe, step, and replacement into the
Postgres database at --database-url, in one transaction. Before committing, it verifies the
load in that same transaction: row counts, and the v1 responses from the new code compared with
the live production API (on DynamoDB) for recipes, replacements, and convert-text output.

Without --commit it's a dry run: it loads and verifies, then rolls back. With --commit it asks
for confirmation and commits only if verification passes. --verify-only re-checks a database
that's already loaded.

Usage (from the repo root; pass the target's UNPOOLED URL, and never save production's in .env):
    .venv/bin/pip install -r etc/requirements-migrate.txt
    .venv/bin/python -m etc.migrate_dynamodb --database-url "$DATABASE_URL_UNPOOLED"
    .venv/bin/python -m etc.migrate_dynamodb --database-url "$DATABASE_URL_UNPOOLED" --commit
    .venv/bin/python -m etc.migrate_dynamodb --database-url "$DATABASE_URL_UNPOOLED" --verify-only

AWS credentials come from the environment (.env locally). The target schema must already be at
the latest Alembic revision (`flask db upgrade`), with empty tables.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone
from decimal import Decimal
from json import dump, loads
from os import makedirs, path, urandom
from sys import exit
from urllib.request import Request, urlopen
from uuid import UUID

from backend import create_app
from backend.config import Config
from backend.database import db, sqlalchemy_url
from backend.functions import replace_text
from backend.models import Recipe, RecipeStep, Replacement
from backend.recipe_routes import RecipeCollectionApi
from backend.replacement_routes import ReplacementCollectionApi
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

# Production DynamoDB. Fixed here on purpose: local .env points at a copy in us-east-2.
DYNAMODB_REGION = 'us-west-1'
PRODUCTION_API_URL = 'https://breadsheet.wl.r.appspot.com'
EXPORTS_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'exports')

# PynamoDB's UTCDateTimeAttribute format, e.g. 2019-02-16T09:00:00.000000+0000
DYNAMODB_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


class MigrationError(Exception):
    pass


## Export ##

def plain(value):
    """Converts boto3's Decimals to int (or float), recursively, so items are JSON-friendly."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


def export_dynamodb() -> dict:
    """Scans both production tables. Read-only."""
    import boto3

    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    export = {}
    for key, table_name in (('recipes', 'Recipe'), ('replacements', 'Replacement')):
        table = dynamodb.Table(table_name)
        items, kwargs = [], {}
        while True:
            response = table.scan(**kwargs)
            items += response['Items']
            if 'LastEvaluatedKey' not in response:
                break
            kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        export[key] = plain(items)

    return export


def save_snapshot(export: dict) -> str:
    """Archives exactly what was exported, in the git-ignored exports/ folder."""
    makedirs(EXPORTS_DIR, exist_ok=True)
    filename = path.join(EXPORTS_DIR, f"dynamodb-{datetime.now(timezone.utc):%Y%m%dt%H%M%S}.json")
    with open(filename, 'w') as file:
        dump(export, file, indent=2, ensure_ascii=False)
    return filename


## Transform ##

def uuid7_at(moment: datetime, offset_ms: int = 0) -> UUID:
    """
    A UUIDv7 whose timestamp is `moment` (plus offset_ms), with random bits as uuid.uuid7() uses.
    Dating each migrated recipe's id to its date_added keeps ids in the same order as the homepage.
    """
    unix_ms = int(moment.timestamp() * 1000) + offset_ms
    rand = int.from_bytes(urandom(10))  # 80 random bits: 12 for rand_a, 62 for rand_b
    value = (unix_ms & 0xFFFF_FFFF_FFFF) << 80 | 0x7 << 76 | (rand >> 62 & 0xFFF) << 64 \
        | 0b10 << 62 | rand & ((1 << 62) - 1)
    return UUID(int=value)


def parse_dynamodb_datetime(value: str) -> datetime:
    return datetime.strptime(value, DYNAMODB_DATETIME_FORMAT).astimezone(timezone.utc)


def blank_to_none(value: str | None) -> str | None:
    """Empty optional strings become NULL; v1 returns null for both."""
    return value if value else None


def to_recipe(item: dict) -> Recipe:
    """
    Converts one DynamoDB Recipe item. Steps keep their list order, which v1 returns as-is;
    a step whose number doesn't match its position stops the migration rather than guessing.
    """
    date_added = parse_dynamodb_datetime(item['date_added'])
    start_time = parse_dynamodb_datetime(item['start_time']) if item.get('start_time') else date_added

    # A few recipes predate last_modified; their date_added is the best available value
    last_modified = parse_dynamodb_datetime(item['last_modified']) if item.get('last_modified') else date_added

    steps = []
    for position, step in enumerate(item.get('steps') or [], start=1):
        if step['number'] != position:
            raise MigrationError(f"{item['name']}: step at position {position} has number {step['number']}")

        then_wait = step.get('then_wait') or 0
        if not isinstance(then_wait, int) or then_wait < 0:
            raise MigrationError(f"{item['name']}: step {position} has invalid then_wait {then_wait!r}")

        # Dated to the recipe, plus the position in ms, so step ids sort in step order
        steps.append(RecipeStep(id=uuid7_at(date_added, offset_ms=position),
                                position=position,
                                text=step['text'],
                                note=blank_to_none(step.get('note')),
                                wait_min=then_wait,
                                wait_max=then_wait))

    return Recipe(id=uuid7_at(date_added),
                  name=item['name'],
                  author=blank_to_none(item.get('author')),
                  source=blank_to_none(item.get('source')),
                  url=blank_to_none(item.get('url')),
                  difficulty=item.get('difficulty') or "Beginner",
                  solve_for_start=item.get('solve_for_start', True),
                  date_added=date_added,
                  start_time=start_time,
                  last_modified=last_modified,
                  steps=steps)


def to_replacement(item: dict) -> Replacement:
    """Copied exactly; leading and trailing whitespace is part of the replacement."""
    return Replacement(scope=item['scope'], old=item['old'], new=item['new'])


## Verify ##

def fetch_json(url: str) -> dict:
    # certifi's CA bundle, since python.org builds of Python on macOS ship without root certificates
    import certifi
    from ssl import create_default_context

    request = Request(url, headers={'User-Agent': 'breadsheet-migration'})
    with urlopen(request, timeout=30, context=create_default_context(cafile=certifi.where())) as response:
        return loads(response.read())


def comparable_recipes(recipes: list) -> list:
    """
    Drops the fields that legitimately differ: ids (new UUIDv7s) and last_modified, which the
    DynamoDB version rewrites on every read.
    """
    output = []
    for recipe in recipes:
        recipe = {k: v for k, v in recipe.items() if k not in ('id', 'last_modified')}
        recipe['steps'] = [{k: v for k, v in step.items() if k != 'step_id'} for step in recipe['steps']]
        output.append(recipe)
    return output


def convert_all_step_text(recipes: list, replacements: dict) -> list:
    """Runs convert-text's replace_text over every step, for each scope."""
    rep_list = [Replacement(**rep) for reps in replacements.values() for rep in reps]
    texts = [step['text'] + "\n" + (step['note'] or "") for recipe in recipes for step in recipe['steps']]
    return [replace_text(t, rep_list, scope) for scope in ('ingredients', 'directions') for t in texts]


def first_difference(expected: list, actual: list) -> str:
    for index, (e, a) in enumerate(zip(expected, actual)):
        if e != a:
            return f"item {index}:\n  production: {e}\n  postgres:   {a}"
    return f"lengths differ: production {len(expected)}, postgres {len(actual)}"


def verify(export: dict, api_url: str) -> list:
    """
    Compares the target database with DynamoDB and the production API. Runs in the current
    session, so it sees an uncommitted load. Returns a list of failures (empty when it passes).
    """
    failures = []

    # Row counts
    counts = {
        'recipes':      db.session.scalar(select(func.count()).select_from(Recipe)),
        'recipe_steps': db.session.scalar(select(func.count()).select_from(RecipeStep)),
        'replacements': db.session.scalar(select(func.count()).select_from(Replacement))
    }
    expected_counts = {
        'recipes':      len(export['recipes']),
        'recipe_steps': sum(len(r.get('steps') or []) for r in export['recipes']),
        'replacements': len(export['replacements'])
    }
    print(f"Row counts: {counts}")
    if counts != expected_counts:
        failures.append(f"Row counts {counts} don't match DynamoDB {expected_counts}")

    # The v1 responses from the new code, served from this session
    new_recipes, status = RecipeCollectionApi().get()
    new_replacements, rep_status = ReplacementCollectionApi().get('all')
    if status != 200 or rep_status != 200:
        failures.append(f"New v1 endpoints returned {status} and {rep_status}")
        return failures

    # The same responses from production (DynamoDB)
    old_recipes = fetch_json(f"{api_url}/api/v1/recipes")
    old_replacements = fetch_json(f"{api_url}/api/v1/replacements/all")
    if len(old_recipes['data']) != len(export['recipes']):
        failures.append(f"Production API has {len(old_recipes['data'])} recipes but the export has "
                        f"{len(export['recipes'])}; did the data change mid-run?")

    # Recipes: everything but ids and last_modified, in homepage order
    old_list, new_list = comparable_recipes(old_recipes['data']), comparable_recipes(new_recipes['data'])
    if old_list == new_list:
        print(f"Recipes: {len(new_list)} match production, in the same order")
    else:
        failures.append(f"Recipes differ from production at {first_difference(old_list, new_list)}")

    # Replacements: the entire response, including order and whitespace
    if old_replacements == new_replacements:
        print(f"Replacements: identical to production "
              f"({', '.join(f'{len(v)} {k}' for k, v in new_replacements['data'].items())})")
    else:
        failures.append("Replacements differ from production")

    # Convert-text: identical output over every step's text and note
    old_converted = convert_all_step_text(old_recipes['data'], old_replacements['data'])
    new_converted = convert_all_step_text(new_recipes['data'], new_replacements['data'])
    if old_converted == new_converted:
        print(f"Convert-text: identical output for {len(new_converted)} conversions")
    else:
        failures.append(f"Convert-text output differs at {first_difference(old_converted, new_converted)}")

    return failures


## Load ##

def check_target(app):
    """The schema must be at the latest migration, with every table empty."""
    from alembic.script import ScriptDirectory

    head = ScriptDirectory.from_config(app.extensions['migrate'].migrate.get_config()).get_current_head()
    current = db.session.scalar(text("SELECT version_num FROM alembic_version"))
    if current != head:
        raise MigrationError(f"Target schema is at {current}, not {head}; run `flask db upgrade` first")

    for model in (Recipe, RecipeStep, Replacement):
        if db.session.scalar(select(func.count()).select_from(model)):
            raise MigrationError(f"Target table {model.__tablename__} isn't empty")


def print_id_mapping(export: dict, recipes: list):
    """Legacy ids aren't stored (per the spec); this is the only record, for curating defaults."""
    print("\nRecipe ids, in homepage order (legacy -> new):")
    pairs = sorted(zip(export['recipes'], recipes), key=lambda pair: pair[1].date_added)
    for item, recipe in pairs:
        print(f"  {item['id']:40} -> {recipe.id}  {recipe.name}")


def main() -> int:
    parser = ArgumentParser(description="Migrate DynamoDB recipes and replacements to Postgres.")
    parser.add_argument('--database-url', required=True, help="Target Postgres; use the unpooled URL")
    parser.add_argument('--api-url', default=PRODUCTION_API_URL, help="v1 API running on DynamoDB")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--commit', action='store_true', help="Commit the load if verification passes")
    mode.add_argument('--verify-only', action='store_true', help="Verify an already-loaded database")
    args = parser.parse_args()

    target_url = sqlalchemy_url(args.database_url)
    target = make_url(target_url)
    print(f"Target: {target.host} / {target.database}")
    print(f"Source: DynamoDB {DYNAMODB_REGION}; production API {args.api_url}\n")

    class TargetConfig(Config):
        SQLALCHEMY_DATABASE_URI = target_url
        MIGRATIONS_DATABASE_URI = target_url

    app = create_app(TargetConfig)

    try:
        export = export_dynamodb()
        print(f"Exported {len(export['recipes'])} recipes and {len(export['replacements'])} replacements")

        with app.app_context(), app.test_request_context():
            if args.verify_only:
                failures = verify(export, args.api_url)
            else:
                check_target(app)
                print(f"Snapshot saved to {save_snapshot(export)}")

                recipes = [to_recipe(item) for item in export['recipes']]
                db.session.add_all(recipes)
                db.session.add_all(to_replacement(item) for item in export['replacements'])
                db.session.flush()
                print("Loaded (not yet committed); verifying...\n")

                failures = verify(export, args.api_url)
                if not failures:
                    print_id_mapping(export, recipes)

            if failures:
                db.session.rollback()
                print("\nVerification FAILED; nothing was committed:")
                for failure in failures:
                    print(f"  - {failure}")
                return 1

            if not args.commit:
                db.session.rollback()
                print("\nVerification passed." + ("" if args.verify_only else
                                                   " Dry run: rolled back. Re-run with --commit to write."))
                return 0

            confirmation = input(f"\nVerification passed. Type the target host ({target.host}) to commit: ")
            if confirmation.strip() != target.host:
                db.session.rollback()
                print("Not confirmed; rolled back.")
                return 1

            db.session.commit()
            print("Committed.")
            return 0

    except MigrationError as e:
        print(f"\nStopped: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
