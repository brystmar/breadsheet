"""Defines recipe-related endpoints for the front end to consume."""
from backend.global_logger import logger
from backend.functions import generate_new_id
from backend.models import Recipe
from flask import request
from flask_restful import Resource, reqparse
from pynamodb.exceptions import PynamoDBException
from dateutil import parser as dateutil_parser
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
        """Add a new recipe."""
        logger.debug(f"Request: {request}.")

        # TODO: Replace with a different parsing package (ex: marshmallow) since RequestParser
        #  will be deprecated: https://flask-restful.readthedocs.io/en/latest/reqparse.html
        # Initialize the parser
        parser = reqparse.RequestParser(bundle_errors=True)

        # Parse the supplied arguments.  Input doesn't require a recipe_id
        args = parse_recipe_args(parser, False)

        try:
            # Create a new recipe from these arguments
            new_recipe = Recipe(id=generate_new_id(),
                                name=args['name'],
                                author=args['author'],
                                source=args['source'],
                                difficulty=args['difficulty'],
                                length=args['length'],
                                date_added=args['date_added'],
                                start_time=args['start_time'],
                                steps=args['steps']
                                )
        except PynamoDBException as e:
            error_msg = f"Error trying to save new recipe.)"
            logger.debug(f"{error_msg}\nData: {args}.\nError: {e}.")
            return {'message': 'Error', 'data': error_msg}, 500

        try:
            # Write this new recipe to the db
            new_recipe.save()

            logger.debug("End of RecipeCollectionApi.post()")
            return {'message': 'Created', 'data': new_recipe.to_dict()}, 201
        except PynamoDBException as e:
            error_msg = f"Error trying to save new recipe.)"
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

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
        except Recipe.DoesNotExist as e:
            error_msg = f"Recipe {recipe_id} not found.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Not Found', 'data': error_msg}, 404

        # Initialize the parser
        parser = reqparse.RequestParser(bundle_errors=True)

        # Parse the provided arguments
        args = parse_recipe_args(parser)

        # TODO: Only update items actually sent as args -- and allow nulls!
        # Update the retrieved recipe with provided data
        recipe.name = args['name'] or recipe.name
        recipe.author = args['author'] or recipe.author
        recipe.source = args['source'] or recipe.source
        recipe.difficulty = args['difficulty'] or recipe.difficulty
        recipe.date_added = args['date_added'] or recipe.date_added
        recipe.start_time = args['start_time'] or recipe.start_time

        # If the steps list changes, re-calculate the recipe length
        if recipe.steps != args['steps']:
            recipe.steps = args['steps']
            recipe.update_length()

        try:
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


def parse_recipe_args(parser, id_required=True):
    """Parse a JSON arguments for a recipe input."""
    # Deconstruct the input
    parser.add_argument('id', required=id_required, store_missing=False)
    parser.add_argument('name', required=True)
    parser.add_argument('author', store_missing=False)
    parser.add_argument('source', store_missing=False)
    parser.add_argument('difficulty', required=True)
    parser.add_argument('length', type=int, store_missing=False)
    parser.add_argument('date_added', store_missing=False)
    parser.add_argument('start_time', store_missing=False)
    parser.add_argument('steps', type=list, store_missing=False)

    args = parser.parse_args()

    args['date_added'] = parse_timestamp(args['date_added'])
    args['start_time'] = parse_timestamp(args['start_time'])

    return args


def parse_timestamp(ts):
    """Given a non-null str input, convert it to a datetime object."""
    if ts:
        # Replace tz suffix with Z, ex: '2019-11-11 02:15:00+00:00' -> '2019-11-11 02:15:00Z'
        if '+' in ts[10:]:
            sign_location = ts.find('+', 10)
            return dateutil_parser.isoparse(ts[:sign_location + 10] + "Z")
        elif '-' in ts[10:]:
            sign_location = ts.find('-', 10)
            return dateutil_parser.isoparse(ts[:sign_location + 10] + "Z")
        else:
            return dateutil_parser.isoparse(ts)
    else:
        # The class __init__ method will handle nulls
        return None
