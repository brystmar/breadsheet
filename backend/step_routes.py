from main import logger
from backend.models import Step, Recipe
from flask import request
from flask_restful import Resource


class StepApi(Resource):
    def get(self, recipe_id, step_number):
        logger.debug(f"Request: {request}.")
        print(self.__repr__())

        # Convert (and validate) step_number to int
        try:
            step_number = int(step_number)
        except ValueError as e:
            return {'message': 'Step must be an integer.', 'data': e.__str__()}, 404

        recipe = Recipe.get(recipe_id)

        try:
            output = recipe.steps[step_number - 1].to_dict()
            logger.debug(f"Recipe found -- End of request: {request.method}")
            return {'message': 'Success', 'data': output}, 200
        except IndexError as e:
            logger.debug(f"Index out of range for step #{step_number}")
            return {'message': f'Step number {step_number} not found.', 'data': e.__str__()}, 404

    def put(self, recipe_id, step_number):
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        new_steps = []
        added = False
        recipe = Recipe.get(recipe_id)

        for step in recipe.steps:
            if step.number == step_number:
                logger.debug(f"Updating step #{step_number} with args: {request.args}")
                new_steps.append(request.args)
                added = True
            else:
                new_steps.append(step)

        if not added:
            logger.debug(f"Adding step #{step_number} with args: {request.args}")
            new_steps.append(request.args)

        recipe.steps = new_steps
        response = recipe.save()

        logger.debug(f"End of request: {request.method}")
        return "OK", 200

    def delete(self, recipe_id, step_number):
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        recipe = Recipe.get(recipe_id)
        response = recipe.steps[step_number - 1].delete()

        return response
