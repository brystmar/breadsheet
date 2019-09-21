import pytest
from app.main.routes import set_when, add_recipe_ui_fields
from app.main.routes import create_tw_forms, create_start_finish_forms
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm
from app.models import Recipe, Step
from datetime import datetime, timedelta
from pynamodb.attributes import ListAttribute


def step_creator(recipe_input: Recipe, steps_to_create, multiplier=1) -> Recipe:
    step_number = 1
    while step_number <= steps_to_create:
        new_step = Step(number=step_number, text=f"step_{step_number}",
                        then_wait=step_number * multiplier)
        recipe_input.steps.append(new_step)
        step_number += 1

    return recipe_input


def test_calculate_recipe_length():
    recipe = Recipe(id="as32342", length=0, steps=[Step(number=1, text="blah", then_wait=0)])
    recipe.update_length(save=False)
    assert recipe.length == 0

    # Add 4 steps
    recipe = step_creator(recipe, 4, 100)
    recipe.update_length(save=False)
    assert recipe.length == 100 + 200 + 300 + 400
