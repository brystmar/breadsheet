"""
A tiny best-effort cache for data that can always be rebuilt: rate-limit counters, and Home Assistant's
idle polls (breadsheet#33, `backend/poll_cache.py`). On App Engine it's the free shared memcache (a legacy bundled service, enabled
in app.yaml); locally and in tests it's an in-process dict. Every call fails open: a cache outage
returns None, which callers treat as "nothing cached".
"""
import logging
from backend.environment import ON_APP_ENGINE
from threading import Lock
from time import monotonic

logger = logging.getLogger(__name__)


class LocalCache:
    """In-process stand-in for memcache, for local runs and tests."""

    def __init__(self):
        self._data: dict[str, tuple[object, float]] = {}
        self._lock = Lock()

    def incr(self, key: str, ttl: int) -> int | None:
        with self._lock:
            value, expires = self._data.get(key, (0, 0.0))
            if expires <= monotonic():
                value, expires = 0, monotonic() + ttl
            self._data[key] = (value + 1, expires)
            return value + 1

    def get(self, key: str):
        with self._lock:
            value, expires = self._data.get(key, (None, 0.0))
            return value if expires > monotonic() else None

    def set(self, key: str, value, ttl: int) -> bool:
        with self._lock:
            self._data[key] = (value, monotonic() + ttl)
            return True

    def add(self, key: str, value, ttl: int) -> bool:
        """Set only if the key isn't there yet; True if this call set it."""
        with self._lock:
            _, expires = self._data.get(key, (None, 0.0))
            if expires > monotonic():
                return False
            self._data[key] = (value, monotonic() + ttl)
            return True

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)

    def clear(self):
        with self._lock:
            self._data.clear()


class MemcacheCache:
    """App Engine shared memcache. Requires app.wsgi_app to be wrapped with wrap_wsgi_app (main.py)."""

    def incr(self, key: str, ttl: int) -> int | None:
        from google.appengine.api import memcache
        try:
            # add() only sets the expiry when the key is new; incr() never touches it
            memcache.add(key, 0, time=ttl)
            value = memcache.incr(key)
        except Exception as e:
            logger.warning("memcache incr failed for %s: %s", key, e)
            return None

        if value is None:
            # The SDK swallows its own RPC errors and returns None, so a disabled or broken memcache
            #   looks like an empty cache. Right after add(), incr() should never return None.
            logger.warning("memcache incr returned nothing for %s; is memcache enabled (app.yaml)?", key)
        return value

    def get(self, key: str):
        from google.appengine.api import memcache
        try:
            return memcache.get(key)
        except Exception as e:
            logger.warning("memcache get failed for %s: %s", key, e)
            return None

    def set(self, key: str, value, ttl: int) -> bool:
        from google.appengine.api import memcache
        try:
            return bool(memcache.set(key, value, time=ttl))
        except Exception as e:
            logger.warning("memcache set failed for %s: %s", key, e)
            return False

    def add(self, key: str, value, ttl: int) -> bool:
        """Set only if the key isn't there yet; True if this call set it."""
        from google.appengine.api import memcache
        try:
            return bool(memcache.add(key, value, time=ttl))
        except Exception as e:
            logger.warning("memcache add failed for %s: %s", key, e)
            return False

    def delete(self, key: str):
        from google.appengine.api import memcache
        try:
            memcache.delete(key)
        except Exception as e:
            logger.warning("memcache delete failed for %s: %s", key, e)


cache = MemcacheCache() if ON_APP_ENGINE else LocalCache()
