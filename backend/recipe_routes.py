"""Defines recipe-related endpoints for the front end to consume."""
from backend.global_logger import logger
from backend.functions import generate_new_id
from backend.models import Recipe
from flask import request
from flask_restful import Resource
from pynamodb.exceptions import PynamoDBException
from datetime import datetime
import json


class RecipeCollectionApi(Resource):
    def get(self) -> json:
        """Return a collection of all recipes."""
        logger.debug(f"Request: {request}.")

        try:
            # Grab all recipes from the db, then sort by id
            recipes = Recipe.scan()
            recipes = sorted(recipes, key=lambda r: r.id)

            # Convert each to a dictionary, compile into a list
            output = []
            for recipe in recipes:
                output.append(recipe.to_dict())

            logger.debug(f"End of RecipeCollectionApi.get()")
            return {'message': 'Success', 'data': output}, 200
        except BaseException as e:
            error_msg = f"Error trying to retrieve or compile recipe list.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def post(self) -> json:
        """Add a new recipe based on the submitted JSON."""
        logger.debug(f"Request: {request}.")

        # Load the provided JSON
        data = json.loads(request.data.decode())
        logger.debug(f"Data submitted: {data}")

        try:
            # Create a new Recipe from the provided data
            now = datetime.utcnow()
            new_recipe = Recipe(id=generate_new_id(),
                                name=data['name'],
                                author=data['author'],
                                source=data['source'],
                                difficulty=data['difficulty'],
                                length=0,
                                date_added=now,
                                start_time=now,
                                steps=[]
                                )

            logger.debug(f"Recipe object created: {new_recipe.__repr__()}.")

        except PynamoDBException as e:
            error_msg = f"Error trying to create new recipe."
            logger.debug(f"{error_msg}\nData: {data}.\nError: {e}.")
            return {'message': 'Error', 'data': error_msg}, 500
        except BaseException as e:
            error_msg = f"Other error in parsing args."
            logger.debug(f"{error_msg}\n{e}.")
            return {'message': 'Error', 'data': error_msg}, 500

        try:
            # Write this new recipe to the db
            new_recipe.save()
            logger.debug(f"Successfully saved new recipe {new_recipe.__repr__()}.")

            logger.debug("End of RecipeCollectionApi.post()")
            return {'message': 'Created', 'data': new_recipe.to_dict()}, 201
        except PynamoDBException as e:
            error_msg = f"Error trying to save new recipe."
            logger.debug(f"{error_msg}\n{new_recipe.__repr__()}: {e}.")
            return {'message': 'Error', 'data': error_msg}, 500


class RecipeApi(Resource):
    def get(self, recipe_id) -> json:
        """Return a single recipe."""
        logger.debug(f"Request: {request}, for id: {recipe_id}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
            return {'message': 'Success', 'data': recipe.to_dict()}, 200
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
        except PynamoDBException as e:
            error_msg = f"Error trying to retrieve recipe {recipe_id}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def put(self, recipe_id) -> json:
        """Update an existing recipe using data from the request."""
        logger.debug(f"Request: {request}.")

        data = json.loads(request.data.decode())
        logger.debug(f"Data submitted: {data}")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            original_recipe = recipe
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
        except Recipe.DoesNotExist as e:
            error_msg = f"Recipe {recipe_id} not found.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Not Found', 'data': error_msg}, 404

        # Update the retrieved recipe with provided data
        # Required fields
        recipe.name = data['name']
        recipe.difficulty = data['difficulty']

        # Optional fields
        if data['author']:
            recipe.author = data['author']
        if data['source']:
            recipe.source = data['source']
        if data['start_time']:
            recipe.start_time = data['start_time']

        # If the steps list was changed, re-calculate the recipe length
        if data['steps']:
            if recipe.steps != data['steps']:
                recipe.steps = data['steps']
                recipe.update_length()

        try:
            # Only write to the db if there's been a change
            if recipe == original_recipe:
                logger.debug(f"Request did not modify {recipe.__repr__()}.")
                return {'message': 'Success', 'data': recipe.to_dict()}, 200

            recipe.save()
            logger.debug(f"Recipe updated: {recipe.__repr__()})")
            return {'message': 'Success', 'data': recipe.to_dict()}, 200
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
        except PynamoDBException as e:
            error_msg = f"Error trying to save recipe {recipe_id}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, recipe_id) -> json:
        """Delete the selected recipe."""
        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

        try:
            footprint = f"{{id: {recipe.id}, name: {recipe.name}}}"
            recipe.delete()
            logger.debug(f"Recipe {footprint} deleted successfully.)")
            return {'message': 'Success', 'data': f'Recipe {footprint} deleted successfully.'}, 200
        except PynamoDBException as e:
            error_msg = f"Error trying to delete recipe {recipe_id}.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
