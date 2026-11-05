"""Unit tests for keys and usernames; session behavior is covered in identity_routes_test.py."""
from backend.identity import (RESERVED_USERNAMES, generate_key, hash_key, key_fingerprint, username_problem)
from hashlib import sha256
from pytest import mark


def test_generate_key():
    key = generate_key()
    assert len(key) == 22  # 128 bits, URL-safe base64
    assert generate_key() != key


def test_hash_key_is_sha256():
    assert hash_key('abc') == sha256(b'abc').digest()
    assert len(hash_key(generate_key())) == 32


def test_key_fingerprint_is_short_and_not_the_hash():
    key_hash = hash_key(generate_key())
    fingerprint = key_fingerprint(key_hash)
    assert len(fingerprint) == 16
    assert fingerprint not in key_hash.hex()


@mark.parametrize('username', ['abc', 'Thomas_B', 'bread-head', '9lives', 'a' * 30, 'A-_'])
def test_valid_usernames(username):
    assert username_problem(username) is None


@mark.parametrize('username', ['ab', 'a' * 31, '_abc', '-abc', 'has space', 'émile', 'dot.name', 'at@me',
                               '', None, 42, 'abc\n'])
def test_invalid_usernames(username):
    assert 'letters, numbers' in username_problem(username)


@mark.parametrize('username', sorted(RESERVED_USERNAMES) + ['ADMIN', 'Breadsheet', 'TBerg'])
def test_reserved_usernames(username):
    assert 'reserved' in username_problem(username)
