"""Tests for the local cache used in development and tests (App Engine uses memcache)."""
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
