import unittest
from app.models import Recipe


class RecipeTestCase(unittest.TestCase):
    def test_attribute_data_types(self):
        recipe_example = Recipe(id="abc123", name="Test Recipe", author="Myself", source="Someone", difficulty="EZ",
                                date_added="2018-01-02")

        self.assertTrue(isinstance(recipe_example.id, str))
        self.assertTrue(isinstance(recipe_example.name, str))
