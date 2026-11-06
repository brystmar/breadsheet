"""Tests for the admin script's pieces that don't need a server, plus an export -> update round trip."""
from backend.recipe_routes_v2_test import RECIPE
from etc.admin_recipes import editable, main, new_key
from hashlib import sha256


def test_new_key_matches_its_hash():
    key, key_hash = new_key()
    assert len(key) >= 43  # 256 bits, URL-safe base64
    assert sha256(key.encode()).hexdigest() == key_hash
    assert new_key()[0] != key


def test_new_key_command_prints_both(capsys):
    main(['new-key'])
    out = capsys.readouterr().out
    assert 'ADMIN_KEY (' in out and 'ADMIN_KEY_HASH (' in out


DETAILED = {**RECIPE, "detail_level": "detailed", "steps": [
    {"text": "Mix", "then_wait": 1800, "wait_min": 1200, "wait_max": 2400, "active_seconds": 600, "needs_presence": True},
    {"text": "Proof", "wait_min": 3600, "wait_max": 5400, "needs_presence": False},  # a range, no Then Wait
]}


def test_an_exported_recipe_updates_cleanly(client, admin_headers):
    starter = client.post('/api/v2/admin/recipes', json={**RECIPE, "name": "Revive a Starter", "category": "prep"},
                          headers=admin_headers).json['recipe']
    created = client.post('/api/v2/admin/recipes', json={**DETAILED, "prerequisites": [starter['id']]},
                          headers=admin_headers).json['recipe']

    body = editable(created)
    assert set(body) == {'id', 'name', 'author', 'source', 'url', 'difficulty', 'detail_level', 'category',
                         'prerequisites', 'steps'}
    assert body['prerequisites'] == [starter['id']]
    recipe_id = body.pop('id')
    response = client.put(f'/api/v2/admin/recipes/{recipe_id}', json=body, headers=admin_headers)
    assert response.status_code == 200

    unchanged = response.json['recipe']
    assert unchanged['steps'] == created['steps']  # detail fields and the missing Then Wait survive
    assert unchanged['steps'][1]['then_wait'] is None
    assert unchanged['prerequisites'] == created['prerequisites']
    assert {k: unchanged[k] for k in body if k != 'steps'} == {k: created[k] for k in body if k != 'steps'}
