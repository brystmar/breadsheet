"""
The frozen /api/v2 contract (breadsheet#32): docs/api-v2.md must describe exactly the routes, error codes, and
object fields the API has. A failure here means the contract changed: if that's intended, it must only add
things (see Stability in the doc), and the doc changes with it.
"""
import re
from backend.bakes_test import at, baker, clock, loaf, started  # noqa: F401 (fixtures)
from backend.recipe_routes_v2_test import create, register
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / 'docs' / 'api-v2.md').read_text()


def section(heading: str) -> str:
    """The doc's text under a `## heading`, up to the next one."""
    match = re.search(rf'^## {heading}\n(.*?)(?=^## |\Z)', DOC, re.S | re.M)
    assert match, f"docs/api-v2.md has no '## {heading}' section"
    return match.group(1)


def documented_fields(name: str) -> set[str]:
    """The fields in an object's table, from its `### \\`name\\`` section."""
    match = re.search(rf'^### `{name}`\n(.*?)(?=^### |\Z)', section('Objects'), re.S | re.M)
    assert match, f"docs/api-v2.md documents no `{name}` object"
    fields = set()
    for cell in re.findall(r'^\| ([^|]+) \|', match.group(1), re.M):
        fields.update(re.findall(r'`([a-z_]+)`', cell))
    return fields


class TestRoutes:
    def test_the_doc_lists_exactly_the_routes_that_exist(self, app):
        documented = set(re.findall(r'^### `([A-Z]+ /api/v2/\S+)`', section('Endpoints'), re.M))
        actual = set()
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/api/v2/'):
                path = re.sub(r'<(?:\w+:)?(\w+)>', r'<\1>', rule.rule)
                actual.update(f'{method} {path}' for method in rule.methods - {'HEAD', 'OPTIONS'})
        assert actual - documented == set(), "Routes missing from docs/api-v2.md"
        assert documented - actual == set(), "docs/api-v2.md lists routes that don't exist"


class TestErrorCodes:
    def test_every_code_the_api_can_return_is_documented(self):
        documented = set(re.findall(r'^\| `([a-z_]+)` \| (?:\d{3}|varies) \|', section('Errors'), re.M))
        raised = set()
        for source in (ROOT / 'backend').glob('*.py'):
            if source.name.endswith('_test.py'):
                continue
            text = source.read_text()
            raised.update(re.findall(r"ApiError\(\d+, '([a-z_]+)'", text))
            raised.update(re.findall(r"error_response\(\d+, '([a-z_]+)'", text))
            raised.update(re.findall(r"code, message = '([a-z_]+)'", text))
        # checked_moment builds `<field>_invalid` for the two client-supplied times
        raised |= {'completed_at_invalid', 'skipped_at_invalid'}
        assert raised - documented == set(), "Error codes missing from docs/api-v2.md"
        assert documented - raised == set(), "docs/api-v2.md lists error codes nothing returns"


class TestObjects:
    """Each object's fields match its table in the doc, so a new field can't ship undocumented."""

    def test_user(self, client):
        assert set(register(client, 'shape').keys()) == documented_fields('user')

    def test_recipes_and_steps(self, client, baker):
        recipe = create(baker).json['recipe']
        summary = baker.get('/api/v2/recipes').json['recipes'][-1]
        assert set(summary) == documented_fields('recipe summary')
        assert set(recipe) == documented_fields('recipe summary') | documented_fields('recipe')
        assert set(recipe['steps'][0]) == documented_fields('recipe step')

    def test_prerequisites(self, baker):
        starter = create(baker, {"name": "Starter", "category": "prep", "steps": [{"text": "Feed"}]}).json['recipe']
        loaf = create(baker, {"name": "Loaf", "prerequisites": [starter['id']], "steps": [{"text": "Mix"}]}).json['recipe']
        assert set(loaf['prerequisites'][0]) == documented_fields('prerequisite')

    def test_bakes_and_steps(self, baker, loaf):
        bake = started(baker, loaf['id'])
        assert set(bake) == documented_fields('bake')
        assert set(bake['steps'][0]) == documented_fields('bake step')
        assert set(bake['steps'][0]['hands_on']) == {'seconds', 'estimated', 'needs_presence'}

    def test_errors(self, app, baker):
        documented = set(re.findall(r'^\| `([a-z_]+)` \| (?:string|object) \|', section('Errors'), re.M))
        assert documented == {'code', 'message', 'fields'}
        signed_out = app.test_client()
        assert set(signed_out.get('/api/v2/session').json) == {'code', 'message'}  # `fields` only for form errors
        assert set(create(baker, {"steps": [{}]}).json) == documented


class TestConnectionObject:
    def test_connection(self, app, baker):
        code = baker.post('/api/v2/pairing-codes', json={}).json['code']
        connection = app.test_client().post('/api/v2/devices', json={'code': code}).json['connection']
        assert set(connection) == documented_fields('connection')


class TestErrorsAreAlwaysJson:
    def test_an_unexpected_error_is_a_json_500(self, client, monkeypatch):
        def broken(*args, **kwargs):
            raise RuntimeError("boom")
        monkeypatch.setattr('backend.recipe_routes_v2.listed', broken)
        response = client.get('/api/v2/recipes')
        assert response.status_code == 500
        assert response.json['code'] == 'internal_error'
        assert 'boom' not in response.json['message']  # internals never leak
        assert response.headers['Cache-Control'] == 'no-store'

    def test_an_oversized_body_is_a_json_413(self, client):
        response = client.post('/api/v2/users', data='{"username": "' + 'a' * (1024 * 1024) + '"}',
                               content_type='application/json')
        assert response.status_code == 413
        assert response.json['code'] == 'body_too_large'

    def test_a_wrong_method_says_which_ones_work(self, client):
        response = client.put('/api/v2/session', json={})
        assert response.status_code == 405
        assert response.json['code'] == 'method_not_allowed'
        assert 'GET' in response.headers['Allow'] and 'GET' in response.json['message']

    def test_an_unknown_path_is_a_json_404(self, client):
        response = client.get('/api/v2/nothing-here')
        assert response.status_code == 404
        assert response.json['code'] == 'not_found'
        assert 'docs/api-v2.md' in response.json['message']
