"""
v2 recipes: default and personal scopes, copy-to-personal, and URL lookups (breadsheet#29), plus
publishing to the community library (breadsheet#58).

- Default recipes (no owner) are visible to everyone and read-only here; the admin key manages them
  (backend/admin_routes.py).
- Personal recipes belong to their owner. Anyone with the link (the id, or the URL's suffix) can view
  and copy one; only the owner can edit or delete it.
- A published personal recipe is also listed in the community library for everyone. Publishing changes
  nothing else: same owner, URL, and edit rights. Copies made from it are unaffected by unpublishing.
- Detail levels and drafts (breadsheet#30). Each step has a Then Wait (`then_wait`), the timing a bake runs
  on, and optionally a range around it plus hands-on time and "needs you home". `detail_level` only
  changes what the UI shows. A draft is visible only to its owner, can be saved incomplete, and must pass
  validation to go live; drafts can't be published.
- Categories, prerequisites and archiving (breadsheet#59). A recipe is `bread` or `prep`; it can list prep
  recipes as prerequisites (alternatives, never enforced). Archived recipes are left out of every list but
  still open by id or URL.
- Writes need a signed-in browser.
"""
import logging
from backend import events
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.identity import current_user
from backend.models import Recipe, RecipePrerequisite, RecipeStep, User, utc_now
from backend.slugs import is_public_suffix, new_public_suffix, slugify
from flask import request
from sqlalchemy import delete, or_, select
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
DETAIL_LEVELS = ('simple', 'detailed')
CATEGORIES = ('bread', 'prep')
MAX_PREREQUISITES = 10
STEP_DETAIL_FIELDS = ('then_wait', 'wait_min', 'wait_max', 'active_seconds', 'needs_presence')
COMMUNITY_LIMIT = 200  # newest first; paging can be added later without breaking clients


## Loading and permissions ##

def require_user(scope: str | None = None) -> User:
    """The signed-in user, or 401. `scope` is what a device token needs here; None means browser-only."""
    user = current_user(scope)
    if user is None:
        raise ApiError(401, 'not_signed_in', "Sign in to do that.")
    return user


def recipe_or_404(recipe_id) -> Recipe:
    """Any recipe by id, drafts included; endpoints that show a recipe use visible_recipe_or_404."""
    try:
        recipe = db.session.get(Recipe, UUID(str(recipe_id)))
    except ValueError:
        recipe = None
    if recipe is None:
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return recipe


def visible_recipe_or_404(recipe_id, user: User | None) -> Recipe:
    """A recipe the caller may see: defaults for everyone, personal for anyone with the link, drafts for the owner."""
    recipe = recipe_or_404(recipe_id)
    if recipe.is_draft and (user is None or recipe.owner_id != user.id):
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


def optional_seconds(step: dict, field: str, prefix: str, problems: dict) -> int | None:
    value = step.get(field)
    return None if value is None else wait_seconds(value, f'{prefix}.{field}', problems)


def validated_waits(step: dict, prefix: str, problems: dict) -> dict:
    """
    The Then Wait and its range. A step can send just `then_wait` (simple), a range around it, or a range
    alone (then_wait null), e.g. an imported "2-4 hours". Sending nothing means a Then Wait of 0. A
    zero-width range is just a Then Wait. A Then Wait outside its range is allowed; responses flag it.
    """
    then_wait = optional_seconds(step, 'then_wait', prefix, problems)
    if 'wait_min' not in step and 'wait_max' not in step:
        then_wait = then_wait or 0
        return {'then_wait': then_wait, 'wait_min': then_wait, 'wait_max': then_wait}

    wait_min = wait_seconds(step.get('wait_min', then_wait or 0), f'{prefix}.wait_min', problems)
    wait_max = wait_seconds(step.get('wait_max', max(wait_min, then_wait or 0)), f'{prefix}.wait_max', problems)
    if wait_min > wait_max:
        problems[f'{prefix}.wait_max'] = "Can't be shorter than the minimum wait."
    if then_wait is None and wait_min == wait_max:
        then_wait = wait_min
    return {'then_wait': then_wait, 'wait_min': wait_min, 'wait_max': wait_max}


def validated_prerequisite_ids(value, problems: dict) -> list[UUID]:
    """The shape of `prerequisites`: a list of distinct recipe ids. check_prerequisites looks them up."""
    if value is None:
        return []
    if not isinstance(value, list):
        problems['prerequisites'] = "Must be a list of recipe ids."
        return []
    if len(value) > MAX_PREREQUISITES:
        problems['prerequisites'] = f"A recipe can list up to {MAX_PREREQUISITES} prerequisites."
        return []
    ids = []
    for i, item in enumerate(value):
        try:
            recipe_id = UUID(item) if isinstance(item, str) else None
        except ValueError:
            recipe_id = None
        if recipe_id is None:
            problems[f'prerequisites[{i}]'] = "Must be a recipe id."
        elif recipe_id in ids:
            problems[f'prerequisites[{i}]'] = "Listed twice."
        else:
            ids.append(recipe_id)
    return ids


def check_prerequisites(values: dict, editor: User | None, recipe: Recipe | None = None):
    """
    Each prerequisite must be a prep recipe the editor can see (a default, or a personal recipe that isn't
    a draft), and not the recipe itself. A default can only list defaults, so a public recipe never depends
    on someone's personal one. `editor` is None for the admin key. Archived recipes are fine: they still open.
    """
    problems = {}
    for i, recipe_id in enumerate(values['prerequisites']):
        field = f'prerequisites[{i}]'
        found = db.session.get(Recipe, recipe_id)
        if found is None or (editor is not None and not found.visible_to(editor)):
            problems[field] = "That recipe doesn't exist."
        elif found.is_draft:
            problems[field] = "Drafts can't be prerequisites."
        elif editor is None and not found.is_default:
            problems[field] = "A default recipe's prerequisites must be default recipes."
        elif recipe is not None and found.id == recipe.id:
            problems[field] = "A recipe can't be its own prerequisite."
        elif found.category != 'prep':
            problems[field] = "Only prep recipes can be prerequisites."
    if problems:
        first = next(iter(problems.values()))
        raise ApiError(400, 'recipe_invalid', f"Check the recipe: {first}", fields=problems)


def validated_recipe(data: dict, drafts_allowed: bool = True) -> dict:
    """
    A create or full-update body, checked and cleaned; raises 400 `recipe_invalid` with per-field messages.
    A draft (`is_draft: true`) skips only the must-be-filled-in checks (the name and step text); types,
    limits and wait ranges always apply.
    """
    problems = {}

    is_draft = data.get('is_draft', False)
    if not isinstance(is_draft, bool):
        problems['is_draft'] = "Must be true or false."
        is_draft = False
    elif is_draft and not drafts_allowed:
        problems['is_draft'] = "Default recipes can't be drafts."

    detail_level = data.get('detail_level') or 'simple'
    if detail_level not in DETAIL_LEVELS:
        problems['detail_level'] = f"Must be one of: {', '.join(DETAIL_LEVELS)}."

    category = data.get('category') or 'bread'
    if category not in CATEGORIES:
        problems['category'] = f"Must be one of: {', '.join(CATEGORIES)}."

    prerequisites = validated_prerequisite_ids(data.get('prerequisites'), problems)
    if prerequisites and category == 'prep':
        problems['prerequisites'] = "Prep recipes can't have prerequisites of their own."

    name = data.get('name')
    if name is None and is_draft:
        name = ''
    if not isinstance(name, str) or (not name.strip() and not is_draft):
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
            if text is None and is_draft:
                text = ''
            if not isinstance(text, str) or (not text.strip() and not is_draft):
                problems[f'{prefix}.text'] = "Describe the step."
                text = ''
            elif len(text.strip()) > MAX_STEP_TEXT:
                problems[f'{prefix}.text'] = f"Must be {MAX_STEP_TEXT} characters or fewer."

            note = optional_text(step, 'note', MAX_NOTE, problems)
            if 'note' in problems:
                problems[f'{prefix}.note'] = problems.pop('note')

            waits = validated_waits(step, prefix, problems)
            active_seconds = optional_seconds(step, 'active_seconds', prefix, problems)
            needs_presence = step.get('needs_presence')
            if needs_presence is not None and not isinstance(needs_presence, bool):
                problems[f'{prefix}.needs_presence'] = "Must be true, false, or null (unknown)."
                needs_presence = None

            steps.append({'id': step.get('id'), 'text': text.strip(), 'note': note, **waits,
                          'active_seconds': active_seconds, 'needs_presence': needs_presence})

    cleaned = {
        'name':       name.strip(),
        'author':     optional_text(data, 'author', MAX_SHORT_TEXT, problems),
        'source':     optional_text(data, 'source', MAX_SHORT_TEXT, problems),
        'url':        url,
        'difficulty': difficulty,
        'detail_level': detail_level,
        'is_draft':   is_draft,
        'category':   category,
        'prerequisites': prerequisites,
        'steps':      steps
    }

    if problems:
        first = next(iter(problems.values()))
        raise ApiError(400, 'recipe_invalid', f"Check the recipe: {first}", fields=problems)
    return cleaned


def apply_recipe(recipe: Recipe, values: dict):
    """
    Replaces a recipe's fields, steps and prerequisites. Steps whose id matches an existing step keep it.
    A prep recipe that becomes bread stops being anyone's prerequisite, just as if it were deleted.
    """
    if recipe.category == 'prep' and values['category'] != 'prep':
        db.session.execute(delete(RecipePrerequisite).where(RecipePrerequisite.prerequisite_recipe_id == recipe.id))

    for field in ('name', 'author', 'source', 'url', 'difficulty', 'detail_level', 'is_draft', 'category'):
        setattr(recipe, field, values[field])

    links = {link.prerequisite_recipe_id: link for link in recipe.prerequisite_links}
    new_links = []
    for position, prerequisite_id in enumerate(values['prerequisites'], start=1):
        link = links.pop(prerequisite_id, None) or RecipePrerequisite(prerequisite_recipe_id=prerequisite_id)
        link.position = position
        new_links.append(link)
    recipe.prerequisite_links = new_links

    existing = {str(step.id): step for step in recipe.steps}
    new_steps = []
    for position, step_values in enumerate(values['steps'], start=1):
        step = existing.pop(str(step_values['id']), None) or RecipeStep()
        step.position = position
        step.text = step_values['text']
        step.note = step_values['note']
        for field in STEP_DETAIL_FIELDS:
            setattr(step, field, step_values[field])
        new_steps.append(step)
    recipe.steps = new_steps


def recipe_body(recipe: Recipe) -> dict:
    """A recipe's current content as a create/update body, for copying and for validating before publish."""
    return {
        'name': recipe.name, 'author': recipe.author, 'source': recipe.source, 'url': recipe.url,
        'difficulty': recipe.difficulty, 'detail_level': recipe.detail_level, 'is_draft': recipe.is_draft,
        'category': recipe.category, 'prerequisites': [str(link.prerequisite_recipe_id) for link in recipe.prerequisite_links],
        'steps': [{'id': None, 'text': s.text, 'note': s.note,
                   **{field: getattr(s, field) for field in STEP_DETAIL_FIELDS}} for s in recipe.steps]
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

def listed(query):
    """Filters a list query: archived recipes are left out, and `category` narrows it."""
    query = query.where(Recipe.archived_at.is_(None))
    category = request.args.get('category')
    if category:
        if category not in CATEGORIES:
            raise ApiError(400, 'category_invalid', f"Pick a category: {', '.join(CATEGORIES)}.")
        query = query.where(Recipe.category == category)
    return name_matches(query, request.args.get('q'))


@api_v2.get('/recipes')
def list_recipes():
    """Defaults plus the caller's own personal recipes, as summaries; `q` and `category` filter it."""
    user = current_user('recipes:read')
    query = select(Recipe)

    visible = Recipe.owner_id.is_(None)
    if user is not None:
        visible = or_(visible, Recipe.owner_id == user.id)
    query = listed(query.where(visible))

    # Defaults first, in homepage order, then the caller's own
    query = query.order_by(Recipe.owner_id.is_not(None), Recipe.date_added, Recipe.id)
    return {'recipes': [recipe.to_v2_summary(user) for recipe in db.session.scalars(query)]}, 200


@api_v2.post('/recipes')
def create_recipe():
    """Create a personal recipe from scratch."""
    user = require_user('recipes:write')
    values = validated_recipe(json_body())
    check_prerequisites(values, user)

    recipe = new_personal_recipe(user, values['name'])
    apply_recipe(recipe, values)
    db.session.add(recipe)
    events.record(events.RECIPE_CREATED, user, recipe_id=recipe.id)
    db.session.commit()
    logger.info("User %s created recipe %s", user.id, recipe.id)
    return {'recipe': recipe.to_v2_dict(user)}, 201


@api_v2.get('/recipes/<recipe_id>')
def get_recipe(recipe_id):
    user = current_user('recipes:read')
    return {'recipe': visible_recipe_or_404(recipe_id, user).to_v2_dict(user)}, 200


@api_v2.put('/recipes/<recipe_id>')
def update_recipe(recipe_id):
    """Replace a personal recipe (owner only). Renaming regenerates the slug; the suffix stays."""
    user = require_user('recipes:write')
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    values = validated_recipe(json_body())
    check_prerequisites(values, user, recipe)
    if values['is_draft'] and recipe.published_at is not None:
        raise ApiError(409, 'recipe_published', "Published recipes can't go back to draft. Unpublish it first.")

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
    user = require_user('recipes:write')
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    events.record(events.RECIPE_DELETED, user, recipe_id=recipe.id)
    db.session.delete(recipe)
    db.session.commit()
    logger.info("User %s deleted recipe %s", user.id, recipe_id)
    return '', 204


@api_v2.post('/recipes/<recipe_id>/copy')
def copy_recipe(recipe_id):
    """Copy any visible recipe into a new, fully independent personal recipe ("Make it mine")."""
    user = require_user('recipes:write')
    source = visible_recipe_or_404(recipe_id, user)

    copy = new_personal_recipe(user, source.name)
    copy.source_recipe_id = source.id
    apply_recipe(copy, recipe_body(source))
    db.session.add(copy)
    events.record(events.RECIPE_COPIED, user, recipe_id=source.id)
    db.session.commit()
    logger.info("User %s copied recipe %s to %s", user.id, source.id, copy.id)
    return {'recipe': copy.to_v2_dict(user)}, 201


@api_v2.get('/recipes/by-slug/<slug>')
def recipe_by_slug(slug):
    """Resolve a default recipe's URL (/recipes/<slug>)."""
    recipe = db.session.scalar(select(Recipe).where(Recipe.owner_id.is_(None), Recipe.slug == slug))
    if recipe is None:
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return {'recipe': recipe.to_v2_dict(current_user('recipes:read'))}, 200


@api_v2.get('/recipes/by-suffix/<suffix>')
def recipe_by_suffix(suffix):
    """Resolve a personal recipe's URL (/recipes/<slug>-<suffix>); the UI redirects if the slug changed."""
    recipe = None
    if is_public_suffix(suffix):
        recipe = db.session.scalar(select(Recipe).where(Recipe.public_suffix == suffix))
    user = current_user('recipes:read')
    if recipe is None or (recipe.is_draft and (user is None or recipe.owner_id != user.id)):
        raise ApiError(404, 'not_found', "That recipe doesn't exist.")
    return {'recipe': recipe.to_v2_dict(user)}, 200


## Community library (breadsheet#58) ##

@api_v2.post('/recipes/<recipe_id>/publish')
def publish_recipe(recipe_id):
    """Publish a personal recipe to the community library (owner only). It must pass validation as it stands."""
    user = require_user('recipes:write')
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)
    if recipe.is_draft:
        raise ApiError(409, 'recipe_is_draft', "Drafts can't be published. Save it as a finished recipe first.")
    validated_recipe(recipe_body(recipe))

    if recipe.published_at is None:
        recipe.published_at = utc_now()
        events.record(events.RECIPE_PUBLISHED, user, recipe_id=recipe.id)
        db.session.commit()
        logger.info("User %s published recipe %s", user.id, recipe.id)
    return {'recipe': recipe.to_v2_dict(user)}, 200


@api_v2.delete('/recipes/<recipe_id>/publish')
def unpublish_recipe(recipe_id):
    """Take a recipe out of the community library (owner only). Copies people made are unaffected."""
    user = require_user('recipes:write')
    recipe = recipe_or_404(recipe_id)
    require_owner(recipe, user)

    if recipe.published_at is not None:
        recipe.published_at = None
        events.record(events.RECIPE_UNPUBLISHED, user, recipe_id=recipe.id)
        db.session.commit()
        logger.info("User %s unpublished recipe %s", user.id, recipe.id)
    return '', 204


@api_v2.get('/community/recipes')
def community_recipes():
    """Published recipes for everyone, newest first, as summaries with the publisher's username; `q` and `category` filter it."""
    query = listed(select(Recipe).where(Recipe.published_at.is_not(None)))
    query = query.order_by(Recipe.published_at.desc(), Recipe.id).limit(COMMUNITY_LIMIT)
    user = current_user('recipes:read')
    return {'recipes': [recipe.to_v2_summary(user) for recipe in db.session.scalars(query)]}, 200
