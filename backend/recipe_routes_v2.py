"""
v2 recipes: default and personal scopes, copy-to-personal, and URL lookups (breadsheet#29), plus
publishing to the community library (breadsheet#58).

- Default recipes (no owner) are visible to everyone and read-only here; the admin key manages them
  (backend/admin_routes.py).
- Personal recipes belong to their owner. Anyone with the link (the id, or the URL's suffix) can view
  and copy one; only the owner can edit or delete it.
- A published personal recipe is also listed in the community library for everyone. Publishing changes
  nothing else: same owner, URL, and edit rights. Copies made from it are unaffected by unpublishing.
- Writes need a signed-in browser.
"""
import logging
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.identity import current_user
from backend.models import Recipe, RecipeStep, User, utc_now
from backend.slugs import is_public_suffix, new_public_suffix, slugify
from flask import request
from sqlalchemy import or_, select
from urllib.parse import urlparse
from uuid import UUID

logger = logging.getLogger(__name__)

DIFFICULTIES = ('Beginner', 'Intermediate', 'Advanced', 'Expert')
MAX_NAME = 200
MAX_SHORT_TEXT = 200      # author, source
MAX_URL = 2000
MAX_STEPS = 100
MAX_STEP_TEXT = 1000
MAX_NOTE = 5000
MAX_WAIT_SECONDS = 30 * 24 * 60 * 60
MAX_QUERY = 100
COMMUNITY_LIMIT = 200  # newest first; paging can be added later without breaking clients


## Loading and permissions ##

def require_user() -> User:
    user = current_user()
    if user is None:
        raise ApiError(401, 'not_signed_in', "Sign in to do that.")
    return user


def recipe_or_404(recipe_id) -> Recipe:
    """Any recipe by id: defaults for everyone, personal recipes for anyone with the link."""
    try:
        recipe = db.session.get(Recipe, UUID(str(recipe_id)))
    except ValueError:
        recipe = None
    if recipe is None:
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return recipe


def require_owner(recipe: Recipe, user: User):
    if recipe.is_default:
        raise ApiError(403, 'default_read_only', "Default recipes can't be edited. Make it mine to get your own copy.")
    if recipe.owner_id != user.id:
        raise ApiError(403, 'not_owner', "Only this recipe's owner can change it. Make it mine to get your own copy.")


## Validation ##

def optional_text(data: dict, field: str, limit: int, problems: dict) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        problems[field] = "Must be text."
        return None
    value = value.strip()
    if len(value) > limit:
        problems[field] = f"Must be {limit} characters or fewer."
    return value or None


def wait_seconds(value, field: str, problems: dict) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_WAIT_SECONDS:
        problems[field] = "Must be a whole number of seconds, from 0 to 30 days."
        return 0
    return value


def validated_recipe(data: dict) -> dict:
    """A create or full-update body, checked and cleaned; raises 400 `recipe_invalid` with per-field messages."""
    problems = {}

    name = data.get('name')
    if not isinstance(name, str) or not name.strip():
        problems['name'] = "Give the recipe a name."
        name = ''
    elif len(name.strip()) > MAX_NAME:
        problems['name'] = f"Must be {MAX_NAME} characters or fewer."

    url = optional_text(data, 'url', MAX_URL, problems)
    if url and 'url' not in problems and urlparse(url).scheme not in ('http', 'https'):
        problems['url'] = "Must be a web address starting with http:// or https://."

    difficulty = data.get('difficulty') or 'Beginner'
    if difficulty not in DIFFICULTIES:
        problems['difficulty'] = f"Must be one of: {', '.join(DIFFICULTIES)}."

    steps_data = data.get('steps', [])
    steps = []
    if not isinstance(steps_data, list):
        problems['steps'] = "Must be a list."
    elif len(steps_data) > MAX_STEPS:
        problems['steps'] = f"A recipe can have up to {MAX_STEPS} steps."
    else:
        for i, step in enumerate(steps_data):
            prefix = f'steps[{i}]'
            if not isinstance(step, dict):
                problems[prefix] = "Must be an object."
                continue

            text = step.get('text')
            if not isinstance(text, str) or not text.strip():
                problems[f'{prefix}.text'] = "Describe the step."
                text = ''
            elif len(text.strip()) > MAX_STEP_TEXT:
                problems[f'{prefix}.text'] = f"Must be {MAX_STEP_TEXT} characters or fewer."

            note = optional_text(step, 'note', MAX_NOTE, problems)
            if 'note' in problems:
                problems[f'{prefix}.note'] = problems.pop('note')

            # Simple steps send one wait (wait_min); wait_max defaults to it
            wait_min = wait_seconds(step.get('wait_min', 0), f'{prefix}.wait_min', problems)
            wait_max = wait_seconds(step.get('wait_max', wait_min), f'{prefix}.wait_max', problems)
            if wait_min > wait_max:
                problems[f'{prefix}.wait_max'] = "Can't be shorter than the minimum wait."

            steps.append({'id': step.get('id'), 'text': text.strip(), 'note': note,
                          'wait_min': wait_min, 'wait_max': wait_max})

    cleaned = {
        'name':       name.strip(),
        'author':     optional_text(data, 'author', MAX_SHORT_TEXT, problems),
        'source':     optional_text(data, 'source', MAX_SHORT_TEXT, problems),
        'url':        url,
        'difficulty': difficulty,
        'steps':      steps
    }

    if problems:
        first = next(iter(problems.values()))
        raise ApiError(400, 'recipe_invalid', f"Check the recipe: {first}", fields=problems)
    return cleaned


def apply_recipe(recipe: Recipe, values: dict):
    """Replaces a recipe's fields and steps. Steps whose id matches an existing step keep it."""
    for field in ('name', 'author', 'source', 'url', 'difficulty'):
        setattr(recipe, field, values[field])

    existing = {str(step.id): step for step in recipe.steps}
    new_steps = []
    for position, step_values in enumerate(values['steps'], start=1):
        step = existing.pop(str(step_values['id']), None) or RecipeStep()
        step.position = position
        step.text = step_values['text']
        step.note = step_values['note']
        step.wait_min = step_values['wait_min']
        step.wait_max = step_values['wait_max']
        new_steps.append(step)
    recipe.steps = new_steps


def recipe_body(recipe: Recipe) -> dict:
    """A recipe's current content as a create/update body, for copying and for validating before publish."""
    return {
        'name': recipe.name, 'author': recipe.author, 'source': recipe.source, 'url': recipe.url,
        'difficulty': recipe.difficulty,
        'steps': [{'id': None, 'text': s.text, 'note': s.note, 'wait_min': s.wait_min, 'wait_max': s.wait_max}
                  for s in recipe.steps]
    }


def name_matches(query, q: str):
    """Filters a recipe query by a case-insensitive name search; % and _ are literal."""
    q = (q or '').strip()[:MAX_QUERY]
    if not q:
        return query
    escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return query.where(Recipe.name.ilike(f'%{escaped}%', escape='\\'))


def new_personal_recipe(owner: User, name: str) -> Recipe:
    now = utc_now()
    return Recipe(owner_id=owner.id, name=name, slug=slugify(name),
                  public_suffix=new_public_suffix(db.session, Recipe),
                  date_added=now, start_time=now, last_modified=now)


## Endpoints ##

@api_v2.get('/recipes')
def list_recipes():
    """Defaults plus the caller's own personal recipes, as summaries; `q` filters by name."""
    user = current_user()
    query = select(Recipe)

    visible = Recipe.owner_id.is_(None)
    if user is not None:
        visible = or_(visible, Recipe.owner_id == user.id)
    query = query.where(visible)

    query = name_matches(query, request.args.get('q'))

    # Defaults first, in homepage order, then the caller's own
    query = query.order_by(Recipe.owner_id.is_not(None), Recipe.date_added, Recipe.id)
    return {'recipes': [recipe.to_v2_summary(user) for recipe in db.session.scalars(query)]}, 200


@api_v2.post('/recipes')
def create_recipe():
    """Create a personal recipe from scratch."""
    user = require_user()
    values = validated_recipe(json_body())

    recipe = new_personal_recipe(user, values['name'])
    apply_recipe(recipe, values)
    db.session.add(recipe)
    db.session.commit()
    logger.info("User %s created recipe %s", user.id, recipe.id)
    return {'recipe': recipe.to_v2_dict(user)}, 201


@api_v2.get('/recipes/<recipe_id>')
def get_recipe(recipe_id):
    return {'recipe': recipe_or_404(recipe_id).to_v2_dict(current_user())}, 200


@api_v2.put('/recipes/<recipe_id>')
def update_recipe(recipe_id):
    """Replace a personal recipe (owner only). Renaming regenerates the slug; the suffix stays."""
    user = require_user()
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    values = validated_recipe(json_body())

    if values['name'] != recipe.name:
        recipe.slug = slugify(values['name'])
    apply_recipe(recipe, values)
    recipe.last_modified = utc_now()
    db.session.commit()
    logger.info("User %s updated recipe %s", user.id, recipe.id)
    return {'recipe': recipe.to_v2_dict(user)}, 200


@api_v2.delete('/recipes/<recipe_id>')
def delete_recipe(recipe_id):
    """Delete a personal recipe (owner only). Copies made from it keep working."""
    user = require_user()
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    db.session.delete(recipe)
    db.session.commit()
    logger.info("User %s deleted recipe %s", user.id, recipe_id)
    return '', 204


@api_v2.post('/recipes/<recipe_id>/copy')
def copy_recipe(recipe_id):
    """Copy any visible recipe into a new, fully independent personal recipe ("Make it mine")."""
    user = require_user()
    source = recipe_or_404(recipe_id)

    copy = new_personal_recipe(user, source.name)
    copy.source_recipe_id = source.id
    apply_recipe(copy, recipe_body(source))
    db.session.add(copy)
    db.session.commit()
    logger.info("User %s copied recipe %s to %s", user.id, source.id, copy.id)
    return {'recipe': copy.to_v2_dict(user)}, 201


@api_v2.get('/recipes/by-slug/<slug>')
def recipe_by_slug(slug):
    """Resolve a default recipe's URL (/recipes/<slug>)."""
    recipe = db.session.scalar(select(Recipe).where(Recipe.owner_id.is_(None), Recipe.slug == slug))
    if recipe is None:
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return {'recipe': recipe.to_v2_dict(current_user())}, 200


@api_v2.get('/recipes/by-suffix/<suffix>')
def recipe_by_suffix(suffix):
    """Resolve a personal recipe's URL (/recipes/<slug>-<suffix>); the UI redirects if the slug changed."""
    recipe = None
    if is_public_suffix(suffix):
        recipe = db.session.scalar(select(Recipe).where(Recipe.public_suffix == suffix))
    if recipe is None:
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return {'recipe': recipe.to_v2_dict(current_user())}, 200


## Community library (breadsheet#58) ##

@api_v2.post('/recipes/<recipe_id>/publish')
def publish_recipe(recipe_id):
    """Publish a personal recipe to the community library (owner only). It must pass validation as it stands."""
    user = require_user()
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    validated_recipe(recipe_body(recipe))

    if recipe.published_at is None:
        recipe.published_at = utc_now()
        db.session.commit()
        logger.info("User %s published recipe %s", user.id, recipe.id)
    return {'recipe': recipe.to_v2_dict(user)}, 200


@api_v2.delete('/recipes/<recipe_id>/publish')
def unpublish_recipe(recipe_id):
    """Take a recipe out of the community library (owner only). Copies people made are unaffected."""
    user = require_user()
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)

    if recipe.published_at is not None:
        recipe.published_at = None
        db.session.commit()
        logger.info("User %s unpublished recipe %s", user.id, recipe.id)
    return '', 204


@api_v2.get('/community/recipes')
def community_recipes():
    """Published recipes for everyone, newest first, as summaries with the publisher's username."""
    query = select(Recipe).where(Recipe.published_at.is_not(None))
    query = name_matches(query, request.args.get('q'))
    query = query.order_by(Recipe.published_at.desc(), Recipe.id).limit(COMMUNITY_LIMIT)
    user = current_user()
    return {'recipes': [recipe.to_v2_summary(user) for recipe in db.session.scalars(query)]}, 200
