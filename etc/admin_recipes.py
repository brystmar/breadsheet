"""
Manage default recipes with the admin key (breadsheet#28), until there's an admin UI.

    python etc/admin_recipes.py new-key                     # a new admin key and its ADMIN_KEY_HASH
    python etc/admin_recipes.py export <id-or-slug> > recipe.json
    python etc/admin_recipes.py update recipe.json          # replaces the default whose id is in the file
    python etc/admin_recipes.py create recipe.json          # a new default; any id in the file is ignored

The file is the v2 recipe body (name, author, source, url, difficulty, detail_level, steps), plus the
recipe's `id`. Steps keep their `id`; drop it to add a new step, or delete the step to remove it. Each step
has its Then Wait (`then_wait`, in seconds), the range around it, and the optional detail fields.

Set ADMIN_KEY for that one command, from your password manager; it never goes in .env. BREADSHEET_API
picks the server, defaulting to production; use http://localhost:5050 against the local app.
Standard library only, so it runs from any Python 3.
"""
import json
import sys
from argparse import ArgumentParser
from hashlib import sha256
from os import environ
from secrets import token_urlsafe
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_API = 'https://api.breadsheet.com'
EDITABLE_FIELDS = ('name', 'author', 'source', 'url', 'difficulty', 'detail_level')
STEP_FIELDS = ('id', 'text', 'note', 'then_wait', 'wait_min', 'wait_max', 'active_seconds', 'needs_presence')


def new_key() -> tuple[str, str]:
    """A 256-bit admin key, and the hex SHA-256 the server is configured with."""
    key = token_urlsafe(32)
    return key, sha256(key.encode('utf-8')).hexdigest()


def editable(recipe: dict) -> dict:
    """The parts of a v2 recipe response that a create or update body takes, plus its id."""
    return {'id': recipe['id'],
            **{field: recipe.get(field) for field in EDITABLE_FIELDS},
            'steps': [{field: step.get(field) for field in STEP_FIELDS} for step in recipe.get('steps', [])]}


def call(method: str, path: str, body: dict | None = None, admin: bool = False) -> dict:
    headers = {'Accept': 'application/json'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if admin:
        key = environ.get('ADMIN_KEY')
        if not key:
            sys.exit("Set ADMIN_KEY for this command (from your password manager).")
        headers['Authorization'] = f'Bearer {key}'

    url = environ.get('BREADSHEET_API', DEFAULT_API).rstrip('/') + '/api/v2' + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    try:
        with urlopen(Request(url, data=data, method=method, headers=headers), timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            problem = json.load(error)
        except ValueError:
            problem = {'message': error.reason}
        details = ''.join(f"\n  {field}: {message}" for field, message in (problem.get('fields') or {}).items())
        sys.exit(f"{method} {path} failed ({error.code}): {problem.get('message')}{details}")
    except URLError as error:
        sys.exit(f"Couldn't reach {url}: {error.reason}")


def find_recipe(id_or_slug: str) -> dict:
    """By internal id, or by a default's slug."""
    if len(id_or_slug) == 36 and id_or_slug.count('-') == 4:
        return call('GET', f'/recipes/{quote(id_or_slug)}')['recipe']
    return call('GET', f'/recipes/by-slug/{quote(id_or_slug)}')['recipe']


def read_body(path: str) -> dict:
    with open(path, encoding='utf-8') as file:
        return json.load(file)


def show(recipe: dict):
    print(f"{recipe['name']}  {recipe['path']}  ({len(recipe['steps'])} steps, id {recipe['id']})", file=sys.stderr)


def main(argv=None):
    parser = ArgumentParser(description="Manage default recipes with the admin key.")
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('new-key', help="print a new admin key and its ADMIN_KEY_HASH")
    commands.add_parser('export', help="print a recipe as an editable JSON body").add_argument('recipe')
    commands.add_parser('update', help="replace a default recipe from a JSON file").add_argument('file')
    commands.add_parser('create', help="create a default recipe from a JSON file").add_argument('file')
    args = parser.parse_args(argv)

    if args.command == 'new-key':
        key, key_hash = new_key()
        print(f"ADMIN_KEY (keep in your password manager): {key}")
        print(f"ADMIN_KEY_HASH (server config): {key_hash}")
    elif args.command == 'export':
        print(json.dumps(editable(find_recipe(args.recipe)), indent=2, ensure_ascii=False))
    elif args.command == 'update':
        body = read_body(args.file)
        recipe_id = body.pop('id', None)
        if not recipe_id:
            sys.exit("The file has no `id`; export the recipe first, or use `create` for a new one.")
        show(call('PUT', f'/admin/recipes/{quote(recipe_id)}', body, admin=True)['recipe'])
    elif args.command == 'create':
        body = read_body(args.file)
        body.pop('id', None)
        show(call('POST', '/admin/recipes', body, admin=True)['recipe'])


if __name__ == '__main__':
    main()
