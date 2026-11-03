from backend.functions import replace_text
from backend.models import Replacement


class TestReplaceText:
    def test_replace_text(self):
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
