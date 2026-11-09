"""Tests for community recipes (breadsheet#58): publish, unpublish, the library, copying, admin unpublish."""
from backend.database import db
from backend.models import Recipe, utc_now
from backend.recipe_routes_v2_test import RECIPE, create, make_default, register
from pytest import fixture, raises
from sqlalchemy.exc import IntegrityError


@fixture
def baker(client):
    register(client, 'baker')
    return client


@fixture
def other(app, client):
    browser = app.test_client()
    register(browser, 'other')
    return browser


def publish(client, recipe_id):
    return client.post(f'/api/v2/recipes/{recipe_id}/publish', json={})


def unpublish(client, recipe_id):
    return client.delete(f'/api/v2/recipes/{recipe_id}/publish', json={})


def library(client, query=''):
    return client.get(f'/api/v2/community/recipes{query}').json['recipes']


class TestPublish:
    def test_owner_publishes_and_everyone_sees_it(self, app, baker):
        recipe = create(baker).json['recipe']
        assert recipe['published_at'] is None

        response = publish(baker, recipe['id'])
        assert response.status_code == 200
        published = response.json['recipe']
        assert published['published_at'] is not None
        assert published['scope'] == 'personal' and published['path'] == recipe['path']  # nothing else changes

        listed = library(app.test_client())  # signed out
        assert [(r['name'], r['owner'], r['is_mine']) for r in listed] == [('Weekend Rye', 'baker', False)]
        assert 'steps' not in listed[0]

    def test_republishing_keeps_the_original_time(self, baker):
        recipe_id = create(baker).json['recipe']['id']
        first = publish(baker, recipe_id).json['recipe']['published_at']
        assert publish(baker, recipe_id).json['recipe']['published_at'] == first

    def test_only_the_owner_publishes(self, app, baker, other):
        recipe_id = create(baker).json['recipe']['id']
        assert publish(other, recipe_id).json['code'] == 'not_owner'
        assert publish(app.test_client(), recipe_id).status_code == 401
        assert library(baker) == []

    def test_defaults_cant_be_published(self, baker):
        default = make_default()
        response = publish(baker, default.id)
        assert response.status_code == 403
        assert response.json['code'] == 'default_read_only'

    def test_must_pass_validation(self, baker):
        # Defaults were never validated; a copy of one with a blank step can't be published until it's fixed
        default = make_default()
        default.steps[0].text = ' '
        db.session.commit()
        copy_id = baker.post(f'/api/v2/recipes/{default.id}/copy', json={}).json['recipe']['id']

        response = publish(baker, copy_id)
        assert response.status_code == 400
        assert response.json['code'] == 'recipe_invalid'
        assert set(response.json['fields']) == {'steps[0].text'}
        assert library(baker) == []

    def test_the_database_refuses_a_published_default(self, app, client):
        with app.app_context():
            default = make_default()
            default.published_at = utc_now()
            with raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestUnpublish:
    def test_owner_unpublishes(self, baker):
        recipe_id = create(baker).json['recipe']['id']
        publish(baker, recipe_id)

        assert unpublish(baker, recipe_id).status_code == 204
        assert library(baker) == []
        assert baker.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['published_at'] is None
        assert unpublish(baker, recipe_id).status_code == 204  # already unpublished: no change

    def test_only_the_owner_unpublishes(self, baker, other):
        recipe_id = create(baker).json['recipe']['id']
        publish(baker, recipe_id)
        assert unpublish(other, recipe_id).json['code'] == 'not_owner'
        assert len(library(baker)) == 1

    def test_deleting_a_published_recipe_removes_it(self, baker):
        recipe_id = create(baker).json['recipe']['id']
        publish(baker, recipe_id)
        baker.delete(f'/api/v2/recipes/{recipe_id}', json={})
        assert library(baker) == []


class TestLibrary:
    def test_newest_first_with_search(self, baker, other):
        older = create(baker, {**RECIPE, "name": "Weekend Rye"}).json['recipe']['id']
        newer = create(other, {**RECIPE, "name": "Seeded Rye"}).json['recipe']['id']
        unlisted = create(other, {**RECIPE, "name": "Private Rye"}).json['recipe']['id']
        publish(baker, older)
        publish(other, newer)

        assert [r['name'] for r in library(baker)] == ['Seeded Rye', 'Weekend Rye']
        assert [r['name'] for r in library(baker, '?q=seed')] == ['Seeded Rye']
        assert library(baker, '?q=%25') == []  # % is literal
        assert unlisted not in [r['id'] for r in library(baker)]

    def test_is_capped(self, baker, monkeypatch):
        monkeypatch.setattr('backend.recipe_routes_v2.COMMUNITY_LIMIT', 2)
        for name in ('One', 'Two', 'Three'):
            publish(baker, create(baker, {**RECIPE, "name": name}).json['recipe']['id'])
        assert [r['name'] for r in library(baker)] == ['Three', 'Two']

    def test_published_recipes_stay_out_of_other_peoples_lists(self, baker, other):
        publish(baker, create(baker).json['recipe']['id'])
        assert other.get('/api/v2/recipes').json['recipes'] == []
        assert other.get('/api/v1/recipes').json['data'] == []

    def test_copy_from_the_community(self, baker, other):
        source_id = create(baker).json['recipe']['id']
        publish(baker, source_id)

        copy = other.post(f'/api/v2/recipes/{source_id}/copy', json={}).json['recipe']
        assert copy['is_mine'] and copy['source_recipe_id'] == source_id
        assert copy['published_at'] is None  # copies start private

        unpublish(baker, source_id)
        assert other.get(f"/api/v2/recipes/{copy['id']}").status_code == 200


class TestAdminUnpublish:
    def test_admin_unpublishes_anyones_recipe(self, baker, admin_headers):
        recipe_id = create(baker).json['recipe']['id']
        publish(baker, recipe_id)

        response = baker.delete(f'/api/v2/admin/recipes/{recipe_id}/publish', json={}, headers=admin_headers)
        assert response.status_code == 204
        assert library(baker) == []
        assert baker.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['name'] == 'Weekend Rye'  # still exists

    def test_needs_the_admin_key(self, baker):
        recipe_id = create(baker).json['recipe']['id']
        publish(baker, recipe_id)
        response = baker.delete(f'/api/v2/admin/recipes/{recipe_id}/publish', json={})
        assert response.status_code == 403  # baker isn't an admin (breadsheet#86)
        assert len(library(baker)) == 1

    def test_unknown_ids(self, client, admin_headers):
        assert client.delete('/api/v2/admin/recipes/nope/publish', json={}, headers=admin_headers).status_code == 404
