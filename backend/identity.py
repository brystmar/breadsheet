"""
Keys, usernames, and browser sessions (breadsheet#26).

A user is a username plus a secret key; whoever holds the key is that user. Keys are 128-bit random
values, so a fast SHA-256 is the right hash (slow password hashes exist to protect weak, human-chosen
passwords). Browsers stay signed in with Flask's signed session cookie, which holds the user id and
a short fingerprint of the key hash, so a future key reset would end every existing session.
"""
from backend.database import db
from backend.models import User, utc_now
from datetime import timedelta
from flask import session
from hashlib import sha256
from hmac import compare_digest
from re import fullmatch
from secrets import token_urlsafe
from sqlalchemy import func, select
from uuid import UUID

KEY_BYTES = 16  # 128 bits, shown as 22 URL-safe characters

USERNAME_PATTERN = r'[A-Za-z0-9][A-Za-z0-9_-]{2,29}'
RESERVED_USERNAMES = frozenset({'admin', 'breadsheet', 'api', 'bread', 'prep', 'root',
                                'brystmar', 'thomas', 'tberg'})

# last_seen_at is a coarse activity marker, so it's written at most this often per user
LAST_SEEN_RESOLUTION = timedelta(days=1)


def generate_key() -> str:
    return token_urlsafe(KEY_BYTES)


def hash_key(key: str) -> bytes:
    return sha256(key.encode('utf-8')).digest()


def key_fingerprint(key_hash: bytes) -> str:
    """A short, non-reversible tag of the key hash, stored in the session cookie."""
    return sha256(b'session:' + key_hash).hexdigest()[:16]


def username_problem(username) -> str | None:
    """Returns why a username isn't allowed, in words a person can act on, or None if it's fine."""
    if not isinstance(username, str) or not fullmatch(USERNAME_PATTERN, username):
        return ("Usernames are 3 to 30 characters: letters, numbers, underscores, and hyphens, "
                "starting with a letter or number.")
    if username.lower() in RESERVED_USERNAMES:
        return "That username is reserved. Please pick another."
    return None


def username_taken(username: str) -> bool:
    return db.session.scalar(select(User.id).where(func.lower(User.username) == username.lower())) is not None


def find_user_by_key(key) -> User | None:
    """The user this key belongs to, or None. Never raises on malformed input."""
    if not isinstance(key, str) or not 16 <= len(key.strip()) <= 128:
        return None

    key_hash = hash_key(key.strip())
    user = db.session.scalar(select(User).where(User.key_hash == key_hash))
    if user is None or not compare_digest(user.key_hash, key_hash):
        return None
    return user


def start_session(user: User):
    """Signs this browser in as the user (a permanent cookie, refreshed on each request)."""
    session.clear()
    session.permanent = True
    session['uid'] = str(user.id)
    session['kf'] = key_fingerprint(user.key_hash)


def end_session():
    session.clear()


def current_user() -> User | None:
    """The signed-in user for this request, or None. Clears sessions that no longer match a user's key."""
    uid, fingerprint = session.get('uid'), session.get('kf')
    if not uid or not fingerprint:
        return None

    try:
        user = db.session.get(User, UUID(uid))
    except ValueError:
        user = None

    if user is None or not compare_digest(key_fingerprint(user.key_hash), str(fingerprint)):
        session.clear()
        return None

    now = utc_now()
    if now - user.last_seen_at >= LAST_SEEN_RESOLUTION:
        user.last_seen_at = now
        db.session.commit()

    return user
