from backend.functions import generate_new_id, replace_text
from backend.models import Replacement


def test_generate_new_id():
    # Run this 100 times to ensure it always returns a 17-character string
    for i in range(100):
        test_id = generate_new_id()
        assert isinstance(test_id, str)
        assert len(test_id) == 17

    # TODO: Validate that the id generated is unique


def test_replace_text():
    # Arrange
    text_input = "Let me show you something neat: 123456789 alpha\nfoobar"
    rep_list = [
        Replacement(scope='ingredients', old='a', new='b'),
        Replacement(scope='ingredients', old='1', new='2'),
        Replacement(scope='ingredients', old='me', new='you'),
        Replacement(scope='directions', old='alpha', new='bravo'),
        Replacement(scope='directions', old='8', new='9'),
        Replacement(scope='directions', old='foo', new='bar')
    ]

    expected_ingredients = "Let you show you soyouthing nebt: 223456789 blphb\nfoobbr"
    expected_directions = "Let me show you something neat: 123456799 bravo\nbarbar"

    # Action & assert
    assert replace_text(text_input, rep_list, 'ingredients') == expected_ingredients
    assert replace_text(text_input, rep_list, 'directions') == expected_directions
