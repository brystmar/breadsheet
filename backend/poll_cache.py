"""
Idle Home Assistant polls without Postgres (breadsheet#33).

HA polls `GET /api/v2/bakes?status=active&alert=fancy` every 15 to 30 minutes even when nothing is baking. If
each poll queried Postgres, Neon would never suspend. So two things live in the shared cache:

- **Device tokens.** After a token checks out against Postgres, its user and scopes are remembered for a day,
  keyed on the token's hash. Revoking a connection forgets it at once. The database check still runs at least
  daily, which is what keeps `last_used_at` within a day.
- **"No active Fancy bakes."** When a poll finds none, the cache notes it, tagged with the user's current Fancy
  generation: a random value replaced whenever a Fancy bake starts or a bake switches to Fancy. A note is
  believed only while it matches the current generation, so a poll that raced a new Fancy bake can't hide it,
  and an evicted or expired generation makes every old note stale.

Everything here can be rebuilt: a missing entry costs one Postgres query. A cached token only ever earns an
empty bake list; every other request checks the token against Postgres.
"""
import logging
from backend.cache import cache
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

TOKEN_TTL = int(timedelta(days=1).total_seconds())
NOTE_TTL = int(timedelta(days=1).total_seconds())
GENERATION_TTL = int(timedelta(days=7).total_seconds())


@dataclass(frozen=True)
class CachedToken:
    user_id: UUID
    scopes: tuple[str, ...]


def _token_key(token_hash: bytes) -> str:
    return f'tok:{token_hash.hex()}'


def _generation_key(user_id) -> str:
    return f'fgen:{user_id}'


def _note_key(user_id) -> str:
    return f'nofancy:{user_id}'


def remember_token(token_hash: bytes, user_id, scopes) -> None:
    cache.set(_token_key(token_hash), (str(user_id), tuple(scopes)), TOKEN_TTL)


def forget_token(token_hash: bytes) -> None:
    cache.delete(_token_key(token_hash))


def cached_token(token_hash: bytes) -> CachedToken | None:
    value = cache.get(_token_key(token_hash))
    try:
        user_id, scopes = value
        return CachedToken(UUID(user_id), tuple(scopes))
    except (TypeError, ValueError):
        return None


def fancy_generation(user_id) -> str | None:
    """The user's current Fancy generation, starting one if there isn't any. None if the cache is unavailable."""
    key = _generation_key(user_id)
    value = cache.get(key)
    if value is None:
        cache.add(key, uuid4().hex, GENERATION_TTL)
        value = cache.get(key)
    return value


def fancy_changed(user_id) -> None:
    """A Fancy bake started, or a bake switched to Fancy: every "no active Fancy bakes" note is now stale."""
    cache.set(_generation_key(user_id), uuid4().hex, GENERATION_TTL)
    cache.delete(_note_key(user_id))


def note_no_fancy(user_id, generation: str | None) -> None:
    """Remember that the user had no active Fancy bakes as of `generation` (read before querying Postgres)."""
    if generation is not None:
        cache.set(_note_key(user_id), generation, NOTE_TTL)


def has_no_fancy(user_id) -> bool:
    """True only if the cache says, for the current generation, that the user has no active Fancy bakes."""
    note = cache.get(_note_key(user_id))
    return note is not None and note == cache.get(_generation_key(user_id))
