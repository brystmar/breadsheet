from backend.routes_main import generate_new_id
from backend.models import Recipe, Step


def test_generate_new_id():
    # Run this 100 times to ensure it always returns a 17-character string
    for i in range(100):
        test_id = generate_new_id()
        assert isinstance(test_id, str)
        assert len(test_id) == 17

        # TODO: Ensure id is unique


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
