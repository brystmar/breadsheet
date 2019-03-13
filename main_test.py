import main


def text_index():
    main.app.testing = True
    client = main.app.test_client()

    r = client.get('/')
    assert r.status_code == 200
    assert 'Future home of the breadsheet!' in r.data.decode('utf-8')
