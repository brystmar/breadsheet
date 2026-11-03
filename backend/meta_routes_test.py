class TestReadmeApi:
    def test_get(self, app):
        response = app.test_client().get('/api/v1/readme')
        assert response.status_code == 200
        assert response.json['message'] == 'Success'
        assert response.json['data'].startswith('<h1>')
        assert response.headers['Access-Control-Allow-Origin'] == '*'
