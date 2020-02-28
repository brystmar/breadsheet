"""Defines step-related endpoints for the front end to consume."""
from backend.global_logger import logger
from backend.models import Step, Recipe
from flask import request
from flask_restful import Resource
import json


class StepApi(Resource):
    def get(self, recipe_id, step_number) -> json:
        """Return a single step from a specified recipe."""
        logger.debug(f"Request: {request}, for recipe_id: {recipe_id}, step: {step_number}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        except Recipe.DoesNotExist as e:
            error_msg = f'Recipe {recipe_id} not found.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except BaseException as e:
            error_msg = f"Unable to retrieve recipe {recipe_id}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        # Convert the provided step_number to int
        try:
            step_number = int(step_number)

        except ValueError as e:
            error_msg = f'Step must be an integer. Provided: {step_number}, {type(step_number)}.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Validation Error', 'data': error_msg}, 422

        # Extract the requested step
        try:
            output = recipe.steps[step_number - 1].to_dict()
            logger.debug(f"Returning step {step_number}.")
            return {'message': 'Success', 'data': output}, 200

        except IndexError as e:
            error_msg = f'Step {step_number} not found.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except BaseException as e:
            error_msg = f"Unable to retrieve step {step_number}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def put(self, recipe_id, step_number) -> json:
        """Add or update one step within a specified recipe."""
        logger.debug(f"Request: {request}, for recipe_id: {recipe_id}, step: {step_number}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        except Recipe.DoesNotExist as e:
            error_msg = f"Recipe {recipe_id} not found.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Not Found', 'data': error_msg}, 404
        except BaseException as e:
            error_msg = f"Unable to retrieve recipe {recipe_id}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        # Convert step_number to int
        try:
            step_number = int(step_number)
        except ValueError as e:
            error_msg = f'Step must be an integer. Provided: {step_number}, {type(step_number)}.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Validation Error', 'data': error_msg}, 422

        # Extract the requested step
        step_to_modify = Step()
        found = False
        index = 0

        for step in recipe.steps:
            if step.number == step_number:
                step_to_modify = step
                logger.debug(f"Step {step_number} found, ready to update.")
                index = recipe.steps.index(step)
                found = True
                break

        if not found:
            logger.debug(f"Request is to add a new step: {step_number}.")

            # Append an empty step so it's properly updated below (index = 0)
            recipe.steps.append(step_to_modify)

        # Load the provided JSON
        data = json.loads(request.data.decode())
        logger.debug(f"Data submitted: {data}")

        # Add/update data for this step
        # Required fields
        step_to_modify.number = step_number
        step_to_modify.text = data['text']
        step_to_modify.then_wait = data['then_wait']

        # Optional fields
        if data['note']:
            step_to_modify.note = data['note']
        if data['when']:
            step_to_modify.when = data['when']

        # Update the step on the recipe object
        recipe.steps[index] = step_to_modify

        # Ensure the steps are sorted numerically, and update the recipe length
        recipe.steps = sorted(recipe.steps, key=lambda s: s.number)
        recipe.update_length()

        # Save the recipe with the updated step
        try:
            recipe.save()
            logger.debug(f"Step {step_number} updated.")
            return {'message': 'Success', 'data': f'Step {step_number} updated.'}, 200

        except BaseException as e:
            error_msg = f"Unable to update step {step_number}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, recipe_id, step_number) -> json:
        logger.debug(f"Request: {request}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        except Recipe.DoesNotExist as e:
            error_msg = f"Recipe {recipe_id} not found."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except BaseException as e:
            error_msg = f"Unable to retrieve recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        # Convert step_number to int
        try:
            step_number = int(step_number)
        except ValueError as e:
            error_msg = f'Step must be an integer. Provided: {step_number}, {type(step_number)}.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Validation Error', 'data': error_msg}, 422

        # Create a new list of steps, skipping the step to delete
        found = False
        new_steps = []

        for step in recipe.steps:
            if step.number == step_number:
                logger.debug(f"Step {step_number} found, ready to remove.")
                found = True
            else:
                new_steps.append(step)

        if not found:
            error_msg = f'Step {step_number} not found.'
            logger.debug(f"{error_msg}")
            return {'message': 'Error', 'data': f'Step {step_number} not found.'}, 404

        # Update the list of steps and recipe length
        try:
            # Ensure steps are saved in order
            recipe.steps = sorted(new_steps, key=lambda s: s.number)
            recipe.update_length()

        except BaseException as e:
            error_msg = f'Error updating the list of steps: {recipe.steps}'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        try:
            recipe.save()
            logger.debug(f"Step {step_number} deleted.")
            return {'message': 'Success', 'data': f'Step {step_number} deleted.'}, 200
        except BaseException as e:
            error_msg = f'Error saving {recipe.__repr__()} without step {step_number}.'
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
