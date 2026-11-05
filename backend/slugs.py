"""
Slugs and public suffixes for user-facing recipe URLs (spec: Data model, Slugs and suffixes).

- Defaults: /recipes/<slug>. Slugs are unique among defaults (-2, -3 on collision) and never change.
- Personal recipes: /recipes/<slug>-<suffix>. The 6-character suffix does the lookup, so a rename can
  regenerate the slug and old links still resolve (the UI redirects to the current slug).

The API itself always uses internal ids; slugs and suffixes exist only for URLs.
"""
import re
import unicodedata
from secrets import choice
from sqlalchemy import select

SLUG_MAX_LENGTH = 60
SUFFIX_LENGTH = 6
SUFFIX_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'


def slugify(name: str) -> str:
    """Lowercase and hyphenated, accents stripped (crème -> creme); 'recipe' when nothing usable is left."""
    ascii_name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')
    return slug[:SLUG_MAX_LENGTH].rstrip('-') or 'recipe'


def unique_default_slug(session, name: str) -> str:
    """A slug for a new default recipe, unique among defaults."""
    from backend.models import Recipe

    base = slugify(name)
    taken = set(session.scalars(select(Recipe.slug).where(Recipe.owner_id.is_(None),
                                                          Recipe.slug.like(f'{base}%'))))
    candidate, n = base, 2
    while candidate in taken:
        candidate = f'{base}-{n}'
        n += 1
    return candidate


def new_public_suffix(session, model) -> str:
    """6 random characters from a-z0-9, regenerated if `model`'s table already has them."""
    while True:
        suffix = ''.join(choice(SUFFIX_ALPHABET) for _ in range(SUFFIX_LENGTH))
        if session.scalar(select(model.id).where(model.public_suffix == suffix)) is None:
            return suffix


def is_public_suffix(value: str) -> bool:
    return bool(re.fullmatch(f'[a-z0-9]{{{SUFFIX_LENGTH}}}', value or ''))
