class TestReadmeApi:
    def test_get(self, app):
        response = app.test_client().get('/api/v1/readme')
        assert response.status_code == 200
        assert response.json['message'] == 'Success'
        assert response.json['data'].startswith('<h1>')


class TestCors:
    """Credentialed CORS: allowed origins are echoed back, never a wildcard; others get no CORS headers."""

    def test_allowed_origin(self, app):
        for origin in ('https://breadsheet.com', 'https://www.breadsheet.com'):
            response = app.test_client().get('/api/v1/readme', headers={'Origin': origin})
            assert response.headers['Access-Control-Allow-Origin'] == origin
            assert response.headers['Access-Control-Allow-Credentials'] == 'true'
            assert 'Origin' in response.headers['Vary']

    def test_preflight(self, app):
        response = app.test_client().options('/api/v1/recipes', headers={
            'Origin':                         'https://breadsheet.com',
            'Access-Control-Request-Method':  'PUT',
            'Access-Control-Request-Headers': 'Content-Type'
        })
        assert response.status_code == 200
        assert response.headers['Access-Control-Allow-Origin'] == 'https://breadsheet.com'
        assert response.headers['Access-Control-Allow-Credentials'] == 'true'
        assert 'PUT' in response.headers['Access-Control-Allow-Methods']

    def test_disallowed_origins(self, app):
        for origin in ('https://evil.example', 'http://breadsheet.com', 'https://api.breadsheet.com'):
            response = app.test_client().get('/api/v1/readme', headers={'Origin': origin})
            assert response.status_code == 200
            assert 'Access-Control-Allow-Origin' not in response.headers

    def test_dev_origin_only_when_local(self, app):
        from backend.config import Config
        from backend.environment import local

        assert ('http://localhost:3000' in Config.CORS_ORIGINS) == local
        assert '*' not in Config.CORS_ORIGINS
