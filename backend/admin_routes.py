"""
Admin endpoints for default recipes (breadsheet#28): /api/v2/admin/...

The admin key is a separate secret in server config, not a user role (spec: Identity and ownership,
Admin). Callers send `Authorization: Bearer <admin key>`; the server keeps only the key's SHA-256
(ADMIN_KEY_HASH, as hex) and compares in constant time. Failed attempts are rate limited per IP. With no
hash configured, every admin request is refused.

Archiving a default (breadsheet#59) and unpublishing community recipes (breadsheet#58) arrive with the
columns they need. Day to day, etc/admin_recipes.py calls these endpoints.
"""
import hmac
import logging
from backend import rate_limits
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.identity import hash_key
from backend.models import Recipe, utc_now
from backend.recipe_routes_v2 import apply_recipe, recipe_or_404, validated_recipe
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


def require_admin():
    """Refuses the request unless it carries the admin key. Never logs the header."""
    rate_limits.enforce(rate_limits.ADMIN_FAILURES, "Too many admin attempts from this network. Wait a bit.")

    scheme, _, key = request.headers.get('Authorization', '').partition(' ')
    expected = configured_hash()
    if expected is None:
        logger.warning("Admin request refused: ADMIN_KEY_HASH isn't configured")
    if expected is None or scheme.lower() != 'bearer' or not key.strip() \
            or not hmac.compare_digest(hash_key(key.strip()), expected):
        rate_limits.record(rate_limits.ADMIN_FAILURES)
        logger.warning("Admin request refused: missing or invalid admin key")
        raise ApiError(401, 'admin_key_invalid', KEY_INVALID)


def default_or_404(recipe_id) -> Recipe:
    """Admin endpoints only ever touch defaults; personal recipes don't exist here."""
    recipe = recipe_or_404(recipe_id)
    if not recipe.is_default:
        raise ApiError(404, 'not_found', "That default recipe doesn't exist.")
    return recipe


@api_v2.post('/admin/recipes')
def admin_create_recipe():
    """Create a default recipe. Its slug is unique among defaults and never changes."""
    require_admin()
    values = validated_recipe(json_body())

    now = utc_now()
    recipe = Recipe(name=values['name'], slug=unique_default_slug(db.session, values['name']),
                    date_added=now, start_time=now, last_modified=now)
    apply_recipe(recipe, values)
    db.session.add(recipe)
    db.session.commit()
    logger.info("Admin created default recipe %s", recipe.id)
    return {'recipe': recipe.to_v2_dict()}, 201


@api_v2.put('/admin/recipes/<recipe_id>')
def admin_update_recipe(recipe_id):
    """Replace a default recipe. Renaming keeps the slug, so its URL never changes."""
    require_admin()
    recipe = default_or_404(recipe_id)
    values = validated_recipe(json_body())

    apply_recipe(recipe, values)
    recipe.last_modified = utc_now()
    db.session.commit()
    logger.info("Admin updated default recipe %s", recipe.id)
    return {'recipe': recipe.to_v2_dict()}, 200
