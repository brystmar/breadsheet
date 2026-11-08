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


@mark.parametrize('username', ['abc', 'Thomas_B', 'bread-head', 'baker9', 'a' * 30, 'A-_'])
def test_valid_usernames(username):
    assert username_problem(username) is None


@mark.parametrize('username', ['ab', 'a' * 31, '_abc', '-abc', '9lives', '42', 'has space', 'émile', 'dot.name', 'at@me',
                               '', None, 42, 'abc\n'])
def test_invalid_usernames(username):
    assert 'letters, numbers' in username_problem(username)


@mark.parametrize('username', sorted(RESERVED_USERNAMES) + [
    'ADMIN', 'Breadsheet', 'TBerg', 'test-dev-01', 'Test-Prod-01', 'test-me', 'test_me',
    # Separators don't help (breadsheet#83)
    'sign_in', 'Sign-In', 'T-Berg', 'bry_st_mar', 'Admin_Kitchen', 'administrator9', 'breadsheet-team', 'Bread_Sheet_Official'])
def test_reserved_usernames(username):
    assert 'reserved' in username_problem(username)


# breadsheet#83
@mark.parametrize('username', ['tester', 'testy-baker', 'my-test', 'adam', 'bready', 'teamwork', 'helper', 'Thomas_B',
                               'madmin', 'contactless'])
def test_near_misses_are_fine(username):
    assert username_problem(username) is None


@mark.parametrize('username', ['fuckbread', 'f-u-c-k', 'Sh1tLoaf', 'BIGBITCH', 'ass', 'Ass_Baker', 'baker-asses',
                               'crusty-d1ck', 'hell', 'retard', 'cum-bread', 'spic'])
def test_the_word_filter(username):
    assert username_problem(username) == "That username isn't available. Please pick another."


@mark.parametrize('username', ['Scunthorpe_x', 'assessment', 'Peacock', 'hello', 'analysis', 'spicebread',
                               'dough-retarder', 'Dickens', 'cucumber', 'Sussex', 'grapes', 'shellfish', 'cocktail',
                               'raccoon', 'Hancock', 'title', 'classy', 'bass-baker', 'Pakistani', 'fagioli'])
def test_the_word_filter_leaves_innocent_names_alone(username):
    assert username_problem(username) is None
