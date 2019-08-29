import unittest
from datetime import datetime, date
import os
import sys
sys.path.append(os.path.abspath('..'))
from app.models import Recipe


class TestRecipe(unittest.TestCase):
    def test_meta_attributes(self):
        # Meta attributes
        self.assertTrue(Recipe.Meta.table_name == 'Recipe')
        self.assertTrue(Recipe.Meta.region == 'us-west-2')

    def test_attribute_data_types(self):
        # Primary attributes
        recipe_example = Recipe(id="abc123", name="Test Recipe", author="Myself", source="Someone", difficulty="EZ")
        self.assertTrue(isinstance(recipe_example.id, str))
        self.assertTrue(isinstance(recipe_example.name, str))
        self.assertTrue(isinstance(recipe_example.author, str))
        self.assertTrue(isinstance(recipe_example.source, str))
        self.assertTrue(isinstance(recipe_example.difficulty, str))

        # Implicit attributes
        self.assertTrue(isinstance(recipe_example.date_added, date))
        self.assertTrue(isinstance(recipe_example.start_time, datetime))
        self.assertTrue(recipe_example.finish_time_ui is None)
