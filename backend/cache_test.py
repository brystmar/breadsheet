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


def test_set_add_and_delete():
    cache = LocalCache()
    assert cache.set('k', ('a', 1), ttl=60)
    assert cache.get('k') == ('a', 1)
    assert not cache.add('k', 'other', ttl=60)  # add never overwrites
    cache.delete('k')
    assert cache.add('k', 'new', ttl=60)
    assert cache.get('k') == 'new'
    cache.delete('missing')  # deleting nothing is fine


def test_add_replaces_an_expired_entry():
    cache = LocalCache()
    with patch('backend.cache.monotonic', return_value=1000.0):
        cache.set('k', 'old', ttl=60)
    with patch('backend.cache.monotonic', return_value=1061.0):
        assert cache.add('k', 'new', ttl=60)
        assert cache.get('k') == 'new'


def test_memcache_failures_fail_open(caplog):
    from backend.cache import MemcacheCache
    broken = RuntimeError("down")
    with patch('google.appengine.api.memcache.set', side_effect=broken), \
            patch('google.appengine.api.memcache.add', side_effect=broken), \
            patch('google.appengine.api.memcache.delete', side_effect=broken):
        assert MemcacheCache().set('k', 1, ttl=60) is False
        assert MemcacheCache().add('k', 1, ttl=60) is False
        MemcacheCache().delete('k')
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 3


def test_memcache_set_add_delete_pass_through():
    from backend.cache import MemcacheCache
    with patch('google.appengine.api.memcache.set', return_value=True) as set_, \
            patch('google.appengine.api.memcache.add', return_value=False) as add, \
            patch('google.appengine.api.memcache.delete') as delete:
        assert MemcacheCache().set('k', 'v', ttl=60) is True
        assert MemcacheCache().add('k', 'v', ttl=60) is False
        MemcacheCache().delete('k')
    set_.assert_called_once_with('k', 'v', time=60)
    add.assert_called_once_with('k', 'v', time=60)
    delete.assert_called_once_with('k')
