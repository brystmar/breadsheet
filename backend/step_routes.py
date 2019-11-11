from main import logger
from backend.models import Step, Recipe
from flask import request
from flask_restful import Resource


class StepApi(Resource):
    def get(self, recipe_id, step_number):
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        recipe = Recipe.get(recipe_id)

        for step in recipe.steps:
            if step.number == step_number:
                logger.debug(f"Recipe found -- End of request: {request.method}")
                return step, 200

        logger.debug(f"Recipe not found -- End of request: {request.method}")
        return f"Step {step_number} not found for recipe {recipe.id, recipe.name}.", 404

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
