"""Defines step-related endpoints for the front end to consume."""
from main import logger
from backend.models import Step, Recipe
from flask import request
from flask_restful import Resource, reqparse


class StepApi(Resource):

    def get(self, recipe_id, step_number):
        """Return a single step from a specified recipe."""
        logger.debug(f"Request: {request}, for recipe_id: {recipe_id}, step: {step_number}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {
                       'message': 'Not Found',
                       'data':    f'Recipe {recipe_id} not found.'
                   }, 404
        except BaseException as e:
            error_msg = f"Error trying to retrieve recipe {recipe_id}: {e}.)"
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500

        # Convert step_number to int
        try:
            step_number = int(step_number)
        except ValueError:
            return {
                       'message': 'Validation Error',
                       'data':    f'Step must be an integer. Provided: {step_number}.'
                   }, 422

        # Extract the requested step
        try:
            output = recipe.steps[step_number - 1].to_dict()
            logger.debug(f"Returning step {step_number}.")
            return {'message': 'Success', 'data': output}, 200
        except IndexError:
            logger.debug(f"Index out of range for step {step_number}.")
            return {
                       'message': 'Not Found',
                       'data':    f'Step number {step_number} not found.'
                   }, 404
        except BaseException as e:
            error_msg = f"Error trying to return step {step_number}: {e}.)"
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500

    def put(self, recipe_id, step_number):
        """Add or update one step within a specified recipe."""
        logger.debug(f"Request: {request}, for recipe_id: {recipe_id}, step: {step_number}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {
                       'message': 'Not Found',
                       'data':    f'Recipe {recipe_id} not found.'
                   }, 404
        except BaseException as e:
            error_msg = f"Error trying to retrieve recipe {recipe_id}: {e}.)"
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500

        # Convert step_number to int
        try:
            step_number = int(step_number)
        except ValueError:
            return {
                       'message': 'Validation Error',
                       'data':    f'Step {step_number} must be an integer.'
                   }, 422

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

        # Initialize the parser
        parser = reqparse.RequestParser(bundle_errors=True)

        # Specify the arguments provided
        parser.add_argument('number', required=True, type=int)  # In case this is provided
        parser.add_argument('text', required=True, type=str)
        parser.add_argument('then_wait', type=int, default=0, store_missing=False)
        parser.add_argument('note', store_missing=False)
        parser.add_argument('when', store_missing=False)

        args = parser.parse_args()

        # Add/update data for this step
        step_to_modify.number = step_number
        step_to_modify.text = args['text']
        step_to_modify.then_wait = args['then_wait']
        step_to_modify.note = args['note']
        step_to_modify.when = args['when']

        # Update the step on the recipe object
        recipe.steps[index] = step_to_modify

        # Ensure the steps are sorted numerically, and update the recipe length
        recipe.steps = sorted(recipe.steps, key=lambda s: s.number)
        recipe.update_length()

        # Save the recipe with the updated step
        try:
            recipe.save()
            logger.debug(f"Step {step_number} updated.")
            return {
                       'message': 'Success',
                       'data':    f'Step {step_number} updated.'
                   }, 200
        except BaseException as e:
            return {
                       'message': 'Error',
                       'data':    f'Error updating step {step_number}.\n{e}.'
                   }, 500

    def delete(self, recipe_id, step_number):
        logger.debug(f"Request: {request}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {
                       'message': 'Not Found',
                       'data':    f'Recipe {recipe_id} not found.'
                   }, 404
        except BaseException as e:
            error_msg = f"Error trying to retrieve recipe {recipe_id}: {e}.)"
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500

        # Convert step_number to int
        try:
            step_number = int(step_number)
        except ValueError as e:
            return {
                       'message': 'Validation Error',
                       'data':    f'Step {step_number} must be an integer.'
                   }, 422

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
            logger.debug(f"Step {step_number} not found.")
            return {
                       'message': 'Not Found',
                       'data':    f'Step {step_number} not found.'
                   }, 404

        try:
            # Update the list of steps and recipe length.  Ensure steps are saved in order.
            recipe.steps = sorted(new_steps, key=lambda s: s.number)
            recipe.update_length()
        except BaseException as e:
            logger.debug(f'Error updating the list of steps: {e}')
            return {
                       'message': 'Error',
                       'data':    f'Error updating the list of steps: {e}'
                   }, 500

        try:
            recipe.save()
            logger.debug(f"Step {step_number} deleted.")
            return {
                       'message': 'Success',
                       'data':    f'Step {step_number} deleted.'
                   }, 200
        except BaseException as e:
            error_msg = f'Error saving {recipe.__repr__()} without step {step_number}.\n{e}.'
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500
