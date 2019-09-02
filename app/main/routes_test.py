import pytest
from app.main.routes import calculate_recipe_length, set_when, add_recipe_ui_fields
from app.main.routes import create_tw_forms, create_start_finish_forms
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm
from app.models import Recipe, Step
from datetime import datetime, timedelta


def test_calculate_recipe_length():
    recipe = Recipe()

    assert calculate_recipe_length(recipe) == 0
