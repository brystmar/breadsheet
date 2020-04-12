from backend.functions import generate_new_id, set_when, replace_text
from backend.models import Recipe, Step


def test_generate_new_id():
    # Run this 100 times to ensure it always returns a 17-character string
    for i in range(100):
        test_id = generate_new_id()
        assert isinstance(test_id, str)
        assert len(test_id) == 17

        # TODO: Ensure id is unique


def test_replace_text():
    # Arrange
    text_input = "Let me show you something neat: 123456789 alpha\nfoobar"
    rep_list = [
        {
            'scope': 'ingredients',
            'old': 'a',
            'new': 'b'
        },
        {
            'scope': 'ingredients',
            'old': '1',
            'new': '2'
        },
        {
            'scope': 'ingredients',
            'old': 'me',
            'new': 'you'
        },
        {
            'scope': 'directions',
            'old': 'alpha',
            'new': 'bravo'
        },
        {
            'scope': 'directions',
            'old': '8',
            'new': '9'
        },
        {
            'scope': 'directions',
            'old': 'foo',
            'new': 'bar'
        }
    ]

    expected_ingredients = "Let you show you something nebt: 223456789 blphb\nfoobbr"
    expected_directions = "Let me show you something neat: 123456799 bravo\nbarbar"

    # Action & assert
    assert replace_text(text_input, rep_list, 'ingredients') == expected_ingredients
    assert replace_text(text_input, rep_list, 'directions') == expected_directions
