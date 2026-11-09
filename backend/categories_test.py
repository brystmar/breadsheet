"""Tests for recipe categories, prerequisites, and archiving (breadsheet#59)."""
from backend.database import db
from backend.models import Recipe, RecipePrerequisite, utc_now
from backend.recipe_routes_v2_test import RECIPE, create, make_default, register
from pytest import fixture, raises
from sqlalchemy.exc import IntegrityError
from uuid import UUID

PREP = {**RECIPE, "name": "Revive a Starter", "category": "prep"}


@fixture
def baker(client):
    register(client, 'baker')
    return client


@fixture
def other(app, client):
    browser = app.test_client()
    register(browser, 'other')
    return browser


def admin_create(client, headers, body):
    response = client.post('/api/v2/admin/recipes', json=body, headers=headers)
    assert response.status_code == 201, response.json
    return response.json['recipe']


def with_prerequisites(*ids, **fields):
    return {**RECIPE, **fields, "prerequisites": list(ids)}


def names(response):
    return [r['name'] for r in response.json['recipes']]


class TestCategories:
    def test_bread_by_default(self, baker):
        recipe = create(baker).json['recipe']
        assert recipe['category'] == 'bread'
        assert recipe['prerequisites'] == [] and recipe['prerequisite_ids'] == []

    def test_prep(self, baker):
        assert create(baker, PREP).json['recipe']['category'] == 'prep'

    def test_unknown_categories_are_refused(self, baker):
        response = create(baker, {**RECIPE, "category": "pastry"})
        assert response.status_code == 400
        assert set(response.json['fields']) == {'category'}

    def test_lists_filter_by_category(self, baker):
        create(baker)
        create(baker, PREP)
        assert names(baker.get('/api/v2/recipes?category=prep')) == ['Revive a Starter']
        assert names(baker.get('/api/v2/recipes?category=bread')) == ['Weekend Rye']

        response = baker.get('/api/v2/recipes?category=pastry')
        assert response.status_code == 400
        assert response.json['code'] == 'category_invalid'

    def test_the_community_list_filters_by_category(self, baker):
        for body in (RECIPE, PREP):
            baker.post(f"/api/v2/recipes/{create(baker, body).json['recipe']['id']}/publish", json={})
        assert names(baker.get('/api/v2/community/recipes?category=prep')) == ['Revive a Starter']
        assert baker.get('/api/v2/community/recipes?category=pastry').json['code'] == 'category_invalid'


class TestPrerequisites:
    def test_listed_in_order_with_links(self, baker, other):
        mine = create(baker, PREP).json['recipe']
        theirs = create(other, {**PREP, "name": "Build a Levain"}).json['recipe']  # anyone's, by link

        recipe = create(baker, with_prerequisites(theirs['id'], mine['id'])).json['recipe']
        assert recipe['prerequisites'] == [
            {"id": theirs['id'], "name": "Build a Levain", "path": theirs['path'], "category": "prep"},
            {"id": mine['id'], "name": "Revive a Starter", "path": mine['path'], "category": "prep"},
        ]
        summary = baker.get('/api/v2/recipes?category=bread').json['recipes'][0]
        assert summary['prerequisite_ids'] == [theirs['id'], mine['id']]

    def test_reordering_and_removing(self, baker):
        one, two = (create(baker, {**PREP, "name": n}).json['recipe']['id'] for n in ('One', 'Two'))
        recipe_id = create(baker, with_prerequisites(one, two)).json['recipe']['id']

        reordered = baker.put(f'/api/v2/recipes/{recipe_id}', json=with_prerequisites(two, one)).json['recipe']
        assert reordered['prerequisite_ids'] == [two, one]
        cleared = baker.put(f'/api/v2/recipes/{recipe_id}', json=RECIPE).json['recipe']
        assert cleared['prerequisite_ids'] == []

    def test_the_rules(self, baker, other):
        bread = create(baker).json['recipe']['id']
        my_draft = create(baker, {**PREP, "is_draft": True}).json['recipe']['id']
        their_draft = create(other, {**PREP, "is_draft": True}).json['recipe']['id']
        prep = create(baker, PREP).json['recipe']['id']

        response = create(baker, with_prerequisites(bread, my_draft, their_draft,
                                                    '00000000-0000-7000-8000-000000000000'))
        assert response.status_code == 400
        assert response.json['fields'] == {
            'prerequisites[0]': "Only prep recipes can be prerequisites.",
            'prerequisites[1]': "Drafts can't be prerequisites.",
            'prerequisites[2]': "That recipe doesn't exist.",
            'prerequisites[3]': "That recipe doesn't exist.",
        }

        # The shape is checked before anything is looked up
        assert create(baker, with_prerequisites(prep, 'not-an-id', 5)).json['fields'] == {
            'prerequisites[1]': "Must be a recipe id.", 'prerequisites[2]': "Must be a recipe id."}

        assert create(baker, with_prerequisites(prep, prep)).json['fields'] == {'prerequisites[1]': "Listed twice."}
        assert 'prerequisites' in create(baker, with_prerequisites(*[prep] * 11)).json['fields']
        assert create(baker, {**PREP, "prerequisites": [prep]}).json['fields'] == {
            'prerequisites': "Prep recipes can't have prerequisites of their own."}

    def test_the_database_refuses_a_self_link(self, app, client):
        with app.app_context():
            default = make_default()
            db.session.add(RecipePrerequisite(recipe_id=default.id, prerequisite_recipe_id=default.id, position=1))
            with raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_a_prerequisite_that_becomes_a_draft_is_hidden_from_others(self, baker, other):
        prep = create(other, PREP).json['recipe']
        recipe_id = create(baker, with_prerequisites(prep['id'])).json['recipe']['id']

        other.put(f"/api/v2/recipes/{prep['id']}", json={**PREP, "is_draft": True})
        assert baker.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['prerequisites'] == []

    def test_a_prep_recipe_that_becomes_bread_stops_being_a_prerequisite(self, baker, other):
        prep = create(other, PREP).json['recipe']
        recipe_id = create(baker, with_prerequisites(prep['id'])).json['recipe']['id']

        other.put(f"/api/v2/recipes/{prep['id']}", json={**PREP, "category": "bread"})
        assert baker.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['prerequisite_ids'] == []

    def test_deleting_a_prerequisite_removes_the_link(self, baker):
        prep_id = create(baker, PREP).json['recipe']['id']
        recipe_id = create(baker, with_prerequisites(prep_id)).json['recipe']['id']
        baker.delete(f'/api/v2/recipes/{prep_id}', json={})
        assert baker.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['prerequisites'] == []

    def test_copies_keep_the_category_and_links(self, baker, other):
        prep_id = create(baker, PREP).json['recipe']['id']
        source_id = create(baker, with_prerequisites(prep_id)).json['recipe']['id']

        copy = other.post(f'/api/v2/recipes/{source_id}/copy', json={}).json['recipe']
        assert copy['category'] == 'bread'
        assert copy['prerequisite_ids'] == [prep_id]  # the original prep recipe, not a copy of it
        assert other.post(f'/api/v2/recipes/{prep_id}/copy', json={}).json['recipe']['category'] == 'prep'

    def test_defaults_can_only_list_defaults(self, baker, client, admin_headers):
        personal_prep = create(baker, PREP).json['recipe']['id']
        response = client.post('/api/v2/admin/recipes', json=with_prerequisites(personal_prep), headers=admin_headers)
        assert response.json['fields'] == {
            'prerequisites[0]': "A default recipe's prerequisites must be default recipes."}

        default_prep = admin_create(client, admin_headers, PREP)['id']
        default = admin_create(client, admin_headers, with_prerequisites(default_prep))
        assert default['prerequisite_ids'] == [default_prep]


class TestArchiving:
    def test_archived_defaults_leave_every_list_but_still_open(self, app, client, admin_headers):
        kept = admin_create(client, admin_headers, RECIPE)
        retired = admin_create(client, admin_headers, {**RECIPE, "name": "Old Rye"})

        assert client.delete(f"/api/v2/admin/recipes/{retired['id']}", json={}, headers=admin_headers).status_code == 204

        signed_out = app.test_client()
        assert names(signed_out.get('/api/v2/recipes')) == ['Weekend Rye']
        assert [r['name'] for r in signed_out.get('/api/v1/recipes').json['data']] == ['Weekend Rye']

        opened = signed_out.get(f"/api/v2/recipes/{retired['id']}").json['recipe']
        assert opened['archived_at'] is not None
        assert signed_out.get('/api/v2/recipes/by-slug/old-rye').status_code == 200
        assert signed_out.get(f"/api/v1/recipe/{retired['id']}").status_code == 200
        assert kept['archived_at'] is None

    def test_archiving_again_keeps_the_time(self, client, admin_headers):
        recipe_id = admin_create(client, admin_headers, RECIPE)['id']
        client.delete(f'/api/v2/admin/recipes/{recipe_id}', json={}, headers=admin_headers)
        first = client.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['archived_at']
        client.delete(f'/api/v2/admin/recipes/{recipe_id}', json={}, headers=admin_headers)
        assert client.get(f'/api/v2/recipes/{recipe_id}').json['recipe']['archived_at'] == first

    def test_archived_recipes_can_still_be_copied_and_listed_as_prerequisites(self, baker, client, admin_headers):
        prep_id = admin_create(client, admin_headers, PREP)['id']
        client.delete(f'/api/v2/admin/recipes/{prep_id}', json={}, headers=admin_headers)

        copy = baker.post(f'/api/v2/recipes/{prep_id}/copy', json={})
        assert copy.status_code == 201
        assert create(baker, with_prerequisites(prep_id)).status_code == 201

    def test_needs_the_key_and_only_touches_defaults(self, baker, client, admin_headers):
        default_id = admin_create(client, admin_headers, RECIPE)['id']
        assert client.delete(f'/api/v2/admin/recipes/{default_id}', json={}).status_code == 403  # baker isn't an admin

        personal_id = create(baker).json['recipe']['id']
        assert client.delete(f'/api/v2/admin/recipes/{personal_id}', json={}, headers=admin_headers).status_code == 404
        assert client.delete('/api/v2/admin/recipes/nope', json={}, headers=admin_headers).status_code == 404

    def test_archived_recipes_leave_the_community_list(self, app, baker):
        recipe_id = create(baker).json['recipe']['id']
        baker.post(f'/api/v2/recipes/{recipe_id}/publish', json={})
        with app.app_context():
            db.session.get(Recipe, UUID(recipe_id)).archived_at = utc_now()
            db.session.commit()
        assert baker.get('/api/v2/community/recipes').json['recipes'] == []
