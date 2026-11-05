"""Tests for slugs and public suffixes."""
from backend.slugs import SUFFIX_LENGTH, is_public_suffix, slugify
from pytest import mark


@mark.parametrize('name, slug', [
    ("Country Sourdough: Pain de Campagne", "country-sourdough-pain-de-campagne"),
    ("Detroit-Style Pan Pizza", "detroit-style-pan-pizza"),
    ("Crème Brûlée Brioche", "creme-brulee-brioche"),
    ("  Lots   of   spaces  ", "lots-of-spaces"),
    ("50% Whole Wheat", "50-whole-wheat"),
    ("!!!", "recipe"),
    ("", "recipe"),
    ("パン", "recipe"),
])
def test_slugify(name, slug):
    assert slugify(name) == slug


def test_slugify_caps_length_without_a_trailing_hyphen():
    slug = slugify("word " * 30)
    assert len(slug) <= 60
    assert not slug.endswith('-')


def test_is_public_suffix():
    assert is_public_suffix('k7qx2m')
    assert not is_public_suffix('K7QX2M')
    assert not is_public_suffix('k7qx2')
    assert not is_public_suffix('k7-x2m')
    assert not is_public_suffix('')
    assert SUFFIX_LENGTH == 6
