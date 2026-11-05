"""Tests for the local cache used in development and tests (App Engine uses memcache)."""
import logging
from backend.cache import LocalCache
from unittest.mock import patch


def test_incr_and_get():
    cache = LocalCache()
    assert cache.get('k') is None
    assert cache.incr('k', ttl=60) == 1
    assert cache.incr('k', ttl=60) == 2
    assert cache.get('k') == 2


def test_entries_expire():
    cache = LocalCache()
    with patch('backend.cache.monotonic', return_value=1000.0):
        cache.incr('k', ttl=60)
    with patch('backend.cache.monotonic', return_value=1061.0):
        assert cache.get('k') is None
        assert cache.incr('k', ttl=60) == 1  # a new window starts from zero


def test_clear():
    cache = LocalCache()
    cache.incr('k', ttl=60)
    cache.clear()
    assert cache.get('k') is None


def test_memcache_returning_nothing_is_logged(caplog):
    # The SDK returns None instead of raising when memcache is unavailable; that must not be silent
    from backend.cache import MemcacheCache
    with patch('google.appengine.api.memcache.add', return_value=False), \
            patch('google.appengine.api.memcache.incr', return_value=None):
        assert MemcacheCache().incr('rl:test', ttl=60) is None
    assert ('backend.cache', logging.WARNING,
            "memcache incr returned nothing for rl:test; is memcache enabled (app.yaml)?") in caplog.record_tuples


def test_memcache_incr_returns_the_count(caplog):
    from backend.cache import MemcacheCache
    with patch('google.appengine.api.memcache.add', return_value=True), \
            patch('google.appengine.api.memcache.incr', return_value=3):
        assert MemcacheCache().incr('rl:test', ttl=60) == 3
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
