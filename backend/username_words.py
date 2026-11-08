"""
A light word filter for new usernames (breadsheet#83). Deliberately short: it stops the obvious, and an admin
backstop handles the rest. Words are compared after lowercasing and undoing common digit swaps.

- BLOCKED_ANYWHERE: slurs and the strongest obscenities, refused anywhere in the name, even with `-`/`_`
  between the letters.
- BLOCKED_AS_PARTS: milder or ambiguous words, refused only as the whole name or a whole `-`/`_`-separated
  part (plus a plural `s` or `es`). Matching these anywhere would refuse innocent names like Scunthorpe, assessment,
  peacock, hello, analysis, spicebread, or a dough retarder.
"""
from re import split

DIGIT_SWAPS = str.maketrans('013457', 'oieast')

BLOCKED_ANYWHERE = frozenset({
    'fuck', 'shit', 'bitch', 'whore', 'asshole', 'bastard', 'jizz', 'dildo', 'douche',
    'nigger', 'nigga', 'faggot', 'wetback', 'raghead', 'towelhead', 'hitler', 'kkk',
})

BLOCKED_AS_PARTS = frozenset({
    'ass', 'arse', 'damn', 'hell', 'crap', 'piss', 'dick', 'cock', 'tit', 'boob', 'penis', 'vagina', 'anal',
    'anus', 'sex', 'porn', 'cunt', 'slut', 'rape', 'wank', 'twat', 'bollocks', 'cum', 'nazi',
    'fag', 'homo', 'kike', 'spic', 'chink', 'coon', 'gook', 'dyke', 'tranny', 'beaner', 'paki', 'retard',
})


def _clean(text: str) -> str:
    return text.lower().translate(DIGIT_SWAPS)


def has_blocked_word(username: str) -> bool:
    parts = [_clean(part) for part in split(r'[-_]+', username) if part]
    whole = ''.join(parts)
    if any(word in whole for word in BLOCKED_ANYWHERE):
        return True
    return any(part in BLOCKED_AS_PARTS or part.removesuffix('s') in BLOCKED_AS_PARTS
               or part.removesuffix('es') in BLOCKED_AS_PARTS for part in parts + [whole])
