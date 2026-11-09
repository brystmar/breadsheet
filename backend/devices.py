"""
Home Assistant pairing codes and device tokens (breadsheet#27; spec: Identity and ownership, Security).

A signed-in user gets a short pairing code; HA's config flow exchanges it for a 256-bit device token tied to
that user and carrying all four scopes. Codes and tokens are random, so SHA-256 is the right hash (as for
keys); only hashes are stored. Tokens don't expire; they're revoked.
"""
import re
from backend import poll_cache
from backend.api_v2 import ApiError
from backend.database import db
from backend.models import Connection, utc_now
from datetime import timedelta
from flask import g, request
from hashlib import sha256
from secrets import choice, token_urlsafe
from sqlalchemy import select

DEVICE_SCOPES = ('recipes:read', 'recipes:write', 'bakes:read', 'bakes:write')

# Crockford base32: no I, L, O, or U, so codes are easy to read aloud and type
CODE_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
CODE_LENGTH = 8
CODE_LIFETIME = timedelta(minutes=10)
TOKEN_BYTES = 32  # 256 bits
MAX_LABEL = 60
DEFAULT_LABEL = 'Home Assistant'
LAST_USED_RESOLUTION = timedelta(days=1)

TOKEN_INVALID = "That device token isn't valid, or it was revoked. Pair Home Assistant with breadsheet again."


def new_pairing_code() -> str:
    """A fresh code, shown as XXXX-XXXX."""
    code = ''.join(choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return f'{code[:4]}-{code[4:]}'


def normalized_code(value) -> str | None:
    """A typed code as stored: uppercase, without dashes or spaces, with Crockford's look-alikes read as
    digits (I and L as 1, O as 0). None if it can't be a code."""
    if not isinstance(value, str):
        return None
    code = re.sub(r'[\s-]', '', value).upper().translate(str.maketrans('ILO', '110'))
    if len(code) != CODE_LENGTH or any(char not in CODE_ALPHABET for char in code):
        return None
    return code


def hash_secret(value: str) -> bytes:
    return sha256(value.encode('utf-8')).digest()


def new_device_token() -> str:
    return token_urlsafe(TOKEN_BYTES)


def clean_label(value) -> str:
    """The connection's display name: what HA sent, trimmed, or 'Home Assistant'."""
    if not isinstance(value, str):
        return DEFAULT_LABEL
    label = ' '.join(value.split())[:MAX_LABEL].strip()
    return label or DEFAULT_LABEL


def bearer_token() -> str | None:
    """The device token in `Authorization: Bearer <token>`, if the request sent one."""
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    return token.strip() if scheme.lower() == 'bearer' and token.strip() else None


def device_connection(token: str) -> Connection:
    """The live connection for a device token, remembered for the request; 401 `token_invalid` if none."""
    # Keyed on the token too: Flask's test client can keep one app context (and `g`) across requests
    if g.get('connection_token') != token:
        g.pop('connection', None)
    if 'connection' not in g:
        connection = db.session.scalar(select(Connection).where(Connection.token_hash == hash_secret(token)))
        if connection is None or connection.revoked_at is not None:
            raise ApiError(401, 'token_invalid', TOKEN_INVALID)
        now = utc_now()
        if connection.last_used_at is None or now - connection.last_used_at >= LAST_USED_RESOLUTION:
            connection.last_used_at = now
            db.session.commit()
        # Lets HA's idle polls skip Postgres for a day (breadsheet#33); revoking forgets it
        poll_cache.remember_token(connection.token_hash, connection.user_id, connection.scopes)
        g.connection, g.connection_token = connection, token
    return g.connection


def require_scope(connection: Connection, scope: str | None):
    """A device token may only do what its scopes allow; account, session, and pairing calls need a browser."""
    if scope is None:
        raise ApiError(403, 'scope_missing', "Home Assistant can't do that. Sign in on breadsheet.com instead.")
    if scope not in connection.scopes:
        raise ApiError(403, 'scope_missing', f"This device token doesn't have the `{scope}` scope. Pair again to get it.")


def request_connection() -> Connection | None:
    """The connection this request authenticated with, once current_user() has checked it."""
    return g.get('connection')
