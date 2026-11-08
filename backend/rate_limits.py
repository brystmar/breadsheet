"""Per-IP fixed-window rate limits, counted in the shared cache. A cache outage lets requests through."""
from backend.api_v2 import ApiError
from backend.cache import cache
from backend.environment import ON_APP_ENGINE
from dataclasses import dataclass
from flask import request
from time import time


@dataclass(frozen=True)
class Limit:
    name: str
    max_count: int
    window: int  # seconds


# From the spec's Identity and ownership: Security
SIGN_IN_FAILURES = Limit('sign_in_failures', 10, 15 * 60)
SIGNUPS = Limit('signups', 5, 60 * 60)
USERNAME_CHECKS = Limit('username_checks', 60, 60)
ADMIN_FAILURES = Limit('admin_failures', 10, 15 * 60)
PAIRING_FAILURES = Limit('pairing_failures', 5, 15 * 60)


def client_ip() -> str:
    # App Engine sets this header itself, overwriting anything the client sent.
    #   api.breadsheet.com is DNS-only in Cloudflare, so it's the real client address.
    if ON_APP_ENGINE:
        return request.headers.get('X-Appengine-User-Ip') or request.remote_addr or 'unknown'
    return request.remote_addr or 'unknown'


def _window(limit: Limit) -> tuple[str, int]:
    """This window's cache key, and the seconds until it ends."""
    now = int(time())
    index = now // limit.window
    return f"rl:{limit.name}:{client_ip()}:{index}", (index + 1) * limit.window - now


def retry_after(limit: Limit) -> int | None:
    """Seconds until this client may try again, or None when it's under the limit."""
    key, remaining = _window(limit)
    count = cache.get(key)
    return max(remaining, 1) if count is not None and count >= limit.max_count else None


def record(limit: Limit):
    key, remaining = _window(limit)
    cache.incr(key, ttl=remaining + 60)


def enforce(limit: Limit, message: str):
    """Raises 429 `rate_limited` with Retry-After when this client is over the limit."""
    wait = retry_after(limit)
    if wait is not None:
        raise ApiError(429, 'rate_limited', message, {'Retry-After': str(wait)})
