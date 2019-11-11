"""Defines the API endpoints that the front end will consume."""
from main import logger, breadapp
from backend.functions import generate_new_id
from backend.models import Recipe
from datetime import datetime, timedelta
from flask import request, send_from_directory, redirect, url_for
from flask_restful import Resource
from pynamodb.exceptions import ScanError, TableDoesNotExist
import json


class RecipeCollectionApi(Resource):
    def get(self):
        """Return a collection of all recipes."""
        logger.debug(f"Request: {request}.")
        print(self.__repr__())

        # Grab all recipes from the db, then sort by id
        recipes = Recipe.scan()
        recipes = sorted(recipes, key=lambda r: r.id)

        output = []

        for recipe in recipes:
            output.append(recipe.to_dict())

        logger.debug(f"End of request: {request.method}")
        return output

    def post(self):
        """Add a new recipe."""
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        now = datetime.utcnow()

        form = Recipe()

        # Use the form data submitted to create an instance of the Recipe class
        new_recipe = Recipe(id=generate_new_id(),
                            name=form.name.data,
                            author=form.author.data,
                            source=form.source.data,
                            difficulty=form.difficulty.data,
                            date_added=now,
                            start_time=now,
                            steps=[],
                            length=0)

        # Write this new recipe to the db
        logger.info(f"Writing new recipe {new_recipe.__repr__()} to the database.")
        response = new_recipe.save()

        logger.debug("End of add_recipe()")
        return response


class RecipeApi(Resource):
    def get(self, recipe_id):
        """Return a single recipe."""
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        # Retrieve the recipe from the database
        recipe = Recipe.get(recipe_id)
        logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        recipe.update_length()

        logger.debug(f"End of GET /recipe/{recipe_id}")
        return recipe.to_dict()


@breadapp.route('/get_single_recipe_verbose')
def get_single_recipe_verbose(recipe_id) -> json:
    """Given an id, return the requested recipe as a serialized JSON string."""
    # Input validation
    if not isinstance(recipe_id, str):
        return {
            'Status': '400',
            'Details': {
                'ErrorType': TypeError,
                'Message': 'RecipeId must be a string.'
            }
        }
    
    elif recipe_id == "":
        return {
            'Status': '400',
            'Details': {
                'ErrorType': ValueError,
                'Message': 'RecipeId cannot be an empty string.'
            }
        }

    try:
        output = Recipe.get(recipe_id)
        return {
            'Status': '200',
            'Details': {
                'Data': output.dumps(),
                'Message': 'Success!'
            }
        }

    except Recipe.DoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': Recipe.DoesNotExist,
                'Message': 'Invalid recipe id.'
            }
        }


def get_all_recipes_verbose() -> json:
    """Returns a list of JSON objects, representing every recipe in the database."""

    try:
        recipes = Recipe.scan()
        output = []
        for r in recipes:
            output.append(r.dumps())

        return {
            'Status': '200',
            'Details': {
                'Data': output,
                'Message': 'Success!'
            }
        }

    except ScanError as e:
        return {
            'Status': '400',
            'Details': {
                'Error': str(e),
                'ErrorType': ScanError,
                'Message': 'Scan error on the Recipe table.'
            }
        }

    except TableDoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': TableDoesNotExist,
                'Message': 'Recipe table does not exist.'
            }
        }
