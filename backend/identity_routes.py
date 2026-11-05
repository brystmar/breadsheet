"""Signup and browser sessions: /api/v2/users and /api/v2/session (breadsheet#26)."""
import logging
from backend import rate_limits
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.identity import (current_user, end_session, find_user_by_key, generate_key, hash_key,
                              start_session, username_problem, username_taken)
from backend.models import User
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

USERNAME_TAKEN = "That username is taken. Please pick another."


def rate_limited(limit: rate_limits.Limit, message: str):
    wait = rate_limits.retry_after(limit)
    if wait is not None:
        raise ApiError(429, 'rate_limited', message, {'Retry-After': str(wait)})


@api_v2.post('/users')
def create_user():
    """Create a user and sign this browser in. The key is returned once, here, and never again."""
    rate_limited(rate_limits.SIGNUPS, "Too many new accounts from this network. Try again later.")

    username = json_body().get('username')
    username = username.strip() if isinstance(username, str) else username
    problem = username_problem(username)
    if problem:
        raise ApiError(400, 'username_invalid', problem)
    if username_taken(username):
        raise ApiError(409, 'username_taken', USERNAME_TAKEN)

    key = generate_key()
    user = User(username=username, key_hash=hash_key(key))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Someone claimed the same name (in any case) between the check and the insert
        db.session.rollback()
        raise ApiError(409, 'username_taken', USERNAME_TAKEN)

    rate_limits.record(rate_limits.SIGNUPS)
    start_session(user)
    logger.info("New user %s", user.id)
    return {'user': user.to_dict(), 'key': key}, 201


@api_v2.post('/session')
def sign_in():
    """Exchange a key (from the key link or pasted) for a session cookie."""
    rate_limited(rate_limits.SIGN_IN_FAILURES, "Too many sign-in attempts from this network. Wait a bit and try again.")

    user = find_user_by_key(json_body().get('key'))
    if user is None:
        rate_limits.record(rate_limits.SIGN_IN_FAILURES)
        raise ApiError(401, 'key_invalid', "That key doesn't match any account. Check it and try again.")

    start_session(user)
    return {'user': user.to_dict()}, 200


@api_v2.get('/session')
def who_am_i():
    user = current_user()
    if user is None:
        raise ApiError(401, 'not_signed_in', "This browser isn't signed in. Open your key link to sign in.")
    return {'user': user.to_dict()}, 200


@api_v2.delete('/session')
def sign_out():
    """Sign out this browser only. Other browsers stay signed in."""
    end_session()
    return '', 204
