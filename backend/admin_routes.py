"""
Admin endpoints for default recipes (breadsheet#28): /api/v2/admin/...

Two ways in (spec: Identity and ownership, Admin):
- A signed-in admin's session: users with `is_admin`, granted only by `flask --app main admins` (breadsheet#86).
- The admin key, for scripts: `Authorization: Bearer <admin key>`. The server keeps only the key's SHA-256
  (ADMIN_KEY_HASH, as hex) and compares in constant time. With no hash configured, the key never works.
Device tokens never carry admin power, even an admin's own. Failed keys are rate limited per IP.

The same key unpublishes any community recipe (breadsheet#58) and archives defaults (breadsheet#59).
Day to day, etc/admin_recipes.py calls these endpoints.
"""
import hmac
import logging
from backend import rate_limits
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.devices import bearer_token, token_access
from backend.identity import current_user, hash_key
from backend.models import Recipe, User, utc_now
from sqlalchemy import select
from backend.recipe_routes_v2 import apply_recipe, check_prerequisites, recipe_or_404, validated_recipe
from backend.slugs import unique_default_slug
from flask import current_app, request

logger = logging.getLogger(__name__)

KEY_INVALID = "That admin key isn't valid."


def configured_hash() -> bytes | None:
    value = current_app.config.get('ADMIN_KEY_HASH')
    if not value:
        return None
    try:
        expected = bytes.fromhex(value)
    except ValueError:
        expected = b''
    if len(expected) != 32:
        logger.error("ADMIN_KEY_HASH isn't a 64-character hex SHA-256; refusing admin requests")
        return None
    return expected


ADMIN_REQUIRED = "Only breadsheet admins can do that."


def require_admin() -> User | None:
    """
    Refuses the request unless it comes from a signed-in admin or carries the admin key. Returns the admin
    user, or None for the key. Never logs the header.
    """
    rate_limits.enforce(rate_limits.ADMIN_FAILURES, "Too many admin attempts from this network. Wait a bit.")

    key = bearer_token()
    if key is None and not request.headers.get('Authorization'):
        user = current_user()
        if user is None:
            raise ApiError(401, 'not_signed_in', "Sign in as an admin to do that.")
        if not user.is_admin:
            logger.warning("Admin request refused: user %s isn't an admin", user.id)
            raise ApiError(403, 'admin_required', ADMIN_REQUIRED)
        return user

    expected = configured_hash()
    if key is not None and expected is not None and hmac.compare_digest(hash_key(key), expected):
        return None

    # A device or panel token is never an admin, even an admin's own Home Assistant
    try:
        if key is None:  # a malformed Authorization header counts as a wrong key
            raise ApiError(401, 'admin_key_invalid', KEY_INVALID)
        token_access(key)
    except ApiError:
        rate_limits.record(rate_limits.ADMIN_FAILURES)
        if expected is None:
            logger.warning("Admin request refused: ADMIN_KEY_HASH isn't configured")
        logger.warning("Admin request refused: missing or invalid admin key")
        raise ApiError(401, 'admin_key_invalid', KEY_INVALID)
    raise ApiError(403, 'scope_missing', "Home Assistant can't do admin work. Sign in on breadsheet.com instead.")


def admin_label(admin: User | None) -> str:
    return f"admin {admin.id}" if admin else "the admin key"


def default_or_404(recipe_id) -> Recipe:
    """Admin endpoints only ever touch defaults; personal recipes don't exist here."""
    recipe = recipe_or_404(recipe_id)
    if not recipe.is_default:
        raise ApiError(404, 'not_found', "That default recipe doesn't exist.")
    return recipe


@api_v2.get('/admin/recipes')
def admin_list_recipes():
    """Every default recipe, archived ones included (last), for curation (breadsheet#86)."""
    admin = require_admin()
    defaults = db.session.scalars(select(Recipe).where(Recipe.owner_id.is_(None))
                                  .order_by(Recipe.archived_at.is_not(None), Recipe.name))
    return {'recipes': [recipe.to_v2_summary(viewer=admin) for recipe in defaults]}, 200


@api_v2.post('/admin/recipes')
def admin_create_recipe():
    """Create a default recipe. Its slug is unique among defaults and never changes."""
    admin = require_admin()
    values = validated_recipe(json_body(), drafts_allowed=False)
    check_prerequisites(values, editor=None)

    now = utc_now()
    recipe = Recipe(name=values['name'], slug=unique_default_slug(db.session, values['name']),
                    date_added=now, start_time=now, last_modified=now)
    apply_recipe(recipe, values)
    db.session.add(recipe)
    db.session.commit()
    logger.info("%s created default recipe %s", admin_label(admin).capitalize(), recipe.id)
    return {'recipe': recipe.to_v2_dict()}, 201


@api_v2.put('/admin/recipes/<recipe_id>')
def admin_update_recipe(recipe_id):
    """Replace a default recipe. Renaming keeps the slug, so its URL never changes."""
    admin = require_admin()
    recipe = default_or_404(recipe_id)
    values = validated_recipe(json_body(), drafts_allowed=False)
    check_prerequisites(values, editor=None, recipe=recipe)

    apply_recipe(recipe, values)
    recipe.last_modified = utc_now()
    db.session.commit()
    logger.info("%s updated default recipe %s", admin_label(admin).capitalize(), recipe.id)
    return {'recipe': recipe.to_v2_dict()}, 200


@api_v2.delete('/admin/recipes/<recipe_id>/publish')
def admin_unpublish_recipe(recipe_id):
    """Take any recipe out of the community library. The recipe itself, and copies of it, are untouched."""
    admin = require_admin()
    recipe = recipe_or_404(recipe_id)
    if recipe.published_at is not None:
        recipe.published_at = None
        db.session.commit()
        logger.info("%s unpublished recipe %s", admin_label(admin).capitalize(), recipe.id)
    return '', 204


@api_v2.delete('/admin/recipes/<recipe_id>')
def admin_archive_recipe(recipe_id):
    """
    Archive a default: it leaves every recipe list, v1 and v2, but still opens by id or URL, so links,
    copies and bakes keep working. Archiving again keeps the original time. There's no unarchive endpoint.
    """
    admin = require_admin()
    recipe = default_or_404(recipe_id)
    if recipe.archived_at is None:
        recipe.archived_at = utc_now()
        db.session.commit()
        logger.info("%s archived default recipe %s", admin_label(admin).capitalize(), recipe.id)
    return '', 204
