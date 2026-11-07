"""URLs with doubled slashes must never 500 (Flask-RESTful's error router re-raised Werkzeug's merge-slashes redirect)."""
from pytest import mark


@mark.parametrize('method, path', [
    ('get', '/api/v1//recipes'),
    ('get', '/api/v2//recipes'),
    ('post', '/api/v2/recipes//publish'),
    ('post', '/api/v2/recipes//copy'),
    ('delete', '/api/v2//session'),
])
def test_doubled_slashes_are_a_clean_404(app, method, path):
    response = getattr(app.test_client(), method)(path, json={} if method != 'get' else None)
    assert response.status_code == 404, response.status_code
    if path.startswith('/api/v2'):
        assert response.json['code'] == 'not_found'
