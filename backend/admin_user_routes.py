"""
Admin endpoints for users and metrics (breadsheet#87): /api/v2/admin/users and /api/v2/admin/metrics.

Same access as the other admin routes (require_admin: a signed-in admin, or the admin key). Granting admin
stays command-line only (backend/admin_users.py), so nothing here changes `is_admin`.
"""
import logging
from backend import events
from backend.admin_routes import admin_label, require_admin
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.identity import generate_key, hash_key, normalized_username_column, username_problem
from backend.identity_routes import USERNAME_TAKEN
from backend.metrics import METRICS, run_metrics
from backend.models import BAKE_GRACE, Bake, Recipe, User, normalized_username, utc_now
from backend.smoke_users import is_test_username
from datetime import date, datetime, timedelta
from flask import request
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from uuid import UUID

logger = logging.getLogger(__name__)

ACTIVE_WITHIN = timedelta(days=30)
MAX_USERS = 500


def user_or_404(user_id) -> User:
    try:
        user = db.session.get(User, UUID(str(user_id)))
    except ValueError:
        user = None
    if user is None:
        raise ApiError(404, 'not_found', "That user doesn't exist.")
    return user


def iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def counted(column, *conditions):
    """A correlated count for each user row."""
    return select(func.count()).where(column == User.id, *conditions).correlate(User).scalar_subquery()


@api_v2.get('/admin/users')
def admin_list_users():
    """Users, newest first, with activity and counts. `q` matches names; `active=1`; `tests=0` hides test users."""
    require_admin()
    now = utc_now()
    recipes = counted(Recipe.owner_id)
    published = counted(Recipe.owner_id, Recipe.published_at.is_not(None))
    bakes = counted(Bake.user_id)
    active_bakes = counted(Bake.user_id, Bake.status != 'completed', Bake.projected_end > now - BAKE_GRACE)
    query = select(User, recipes, published, bakes, active_bakes).order_by(User.created_at.desc()).limit(MAX_USERS)

    q = request.args.get('q', '').strip()[:30]
    if q:
        query = query.where(normalized_username_column().contains(normalized_username(q), autoescape=True))
    if request.args.get('active') == '1':
        query = query.where(User.last_seen_at >= now - ACTIVE_WITHIN)
    if request.args.get('tests') == '0':
        query = query.where(~func.lower(User.username).startswith('test-'))

    users = []
    for user, recipe_count, published_count, bake_count, active_count in db.session.execute(query):
        users.append({**user.to_dict(),
                      'last_seen_at':        user.last_seen_at.isoformat(),
                      'is_test':             is_test_username(user.username),
                      'is_active':           user.last_seen_at >= now - ACTIVE_WITHIN,
                      'recipe_count':        recipe_count,
                      'published_count':     published_count,
                      'bake_count':          bake_count,
                      'active_bake_count':   active_count})
    return {'users': users}, 200


@api_v2.post('/admin/users/<user_id>/key')
def admin_reset_key(user_id):
    """
    A new key for someone the admin can verify personally, returned this once. The old key stops working, and
    every session for that user ends (the cookie's key fingerprint no longer matches). Not for yourself.
    """
    admin = require_admin()
    user = user_or_404(user_id)
    if admin is not None and admin.id == user.id:
        raise ApiError(403, 'own_key_reset', "You can't reset your own key here. Sign in with your key, "
                                             "or ask another admin.")
    key = generate_key()
    user.key_hash = hash_key(key)
    events.record(events.KEY_RESET, user)
    db.session.commit()
    logger.info("%s reset the key for user %s", admin_label(admin).capitalize(), user.id)
    return {'user': user.to_dict(), 'key': key}, 200


@api_v2.patch('/admin/users/<user_id>')
def admin_rename_user(user_id):
    """Rename a user: signup's rules, except reserved names are allowed."""
    admin = require_admin()
    user = user_or_404(user_id)
    username = json_body().get('username')
    username = username.strip() if isinstance(username, str) else username
    problem = username_problem(username, allow_reserved=True)
    if problem:
        raise ApiError(400, 'username_invalid', problem)

    taken = select(User.id).where(and_(normalized_username_column() == normalized_username(username),
                                       User.id != user.id))
    if db.session.scalar(taken) is not None:
        raise ApiError(409, 'username_taken', USERNAME_TAKEN)

    user.username = username
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, 'username_taken', USERNAME_TAKEN)
    logger.info("%s renamed user %s", admin_label(admin).capitalize(), user.id)
    return {'user': user.to_dict()}, 200


@api_v2.get('/admin/metrics')
def admin_metrics():
    """The usage metrics, as `flask --app main metrics` prints them: read-only, test users left out."""
    require_admin()
    db.session.commit()  # the read-only transaction must start fresh
    results = run_metrics(db.session)
    # JSON objects come out with sorted keys, so `columns` keeps each query's own column order
    return {'metrics': [{'name': name, 'question': question,
                         'columns': list(results[name][0]) if results[name] else [],
                         'rows': [{key: iso(value) for key, value in row.items()} for row in results[name]]}
                        for name, question, _ in METRICS]}, 200
