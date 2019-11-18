"""Defines the API endpoints that the front end will consume."""
from main import logger, breadapp
from backend.functions import generate_new_id
from backend.models import Recipe
from datetime import datetime, timedelta
from flask import request, send_from_directory, redirect, url_for
from flask_restful import Resource, reqparse
from pynamodb.exceptions import ScanError, TableDoesNotExist
from dateutil import parser as dateutil_parser
import json


class RecipeCollectionApi(Resource):
    def get(self):
        """Return a collection of all recipes."""
        logger.debug(f"Request: {request}.")

        # Grab all recipes from the db, then sort by id
        recipes = Recipe.scan()
        recipes = sorted(recipes, key=lambda r: r.id)

        output = []

        for recipe in recipes:
            output.append(recipe.to_dict())

        logger.debug(f"End of RecipeCollectionApi.get()")
        return {'message': 'Success', 'data': output}, 200

    def post(self):
        """Add a new recipe."""
        logger.debug(f"Request: {request}.")

        # TODO: Replace with a different parsing package (ex: marshmallow) since RequestParser
        #  will be deprecated: https://flask-restful.readthedocs.io/en/latest/reqparse.html
        parser = reqparse.RequestParser(bundle_errors=True)

        args = parse_recipe_args(parser)
        new_recipe = create_recipe_from_args(args)

        # Write this new recipe to the db
        new_recipe.save()

        logger.debug("End of RecipeCollectionApi.post()")
        return {'message': 'Created', 'data': new_recipe.to_dict()}, 201


class RecipeApi(Resource):
    def get(self, recipe_id) -> json:
        """Return a single recipe."""
        logger.debug(f"Request: {request}, for id: {recipe_id}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe.__repr__()})")
            return {'message': 'Success', 'data': recipe.to_dict()}, 200

        except Recipe.DoesNotExist as e:
            logger.debug(f"Recipe {recipe_id} not found.)")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.\n{e}.'}, 404

    def put(self, recipe_id) -> json:
        """Update a recipe."""
        logger.debug(f"Request: {request}.")

        existing_recipe = Recipe.get(recipe_id)
        parser = reqparse.RequestParser(bundle_errors=True)
        args = parse_recipe_args(parser)

        # TODO: Only update items actually sent as args, and allow nulls!
        # Update & save the recipe object
        existing_recipe.name = args['name'] or existing_recipe.name
        existing_recipe.author = args['author'] or existing_recipe.author
        existing_recipe.source = args['source'] or existing_recipe.source
        existing_recipe.difficulty = args['difficulty'] or existing_recipe.difficulty
        existing_recipe.steps = args['steps'] or existing_recipe.steps
        existing_recipe.date_added = args['date_added'] or existing_recipe.date_added
        existing_recipe.start_time = args['start_time'] or existing_recipe.start_time
        existing_recipe.update_length()

        try:
            existing_recipe.save()
            logger.debug(f"Recipe updated: {existing_recipe.__repr__()})")
            return {'message': 'Success', 'data': existing_recipe.to_dict()}, 200
        except Recipe.DoesNotExist as e:
            logger.debug(f"Recipe {existing_recipe.__repr__()} not found.)")
            return {'message': 'Not Found', 'data': f'Recipe {existing_recipe} not found.\n{e}.'}, 404


def parse_recipe_args(parser):
    """Parse a JSON arguments for a recipe input."""
    # Deconstruct the input
    parser.add_argument('id')
    parser.add_argument('name', required=True)
    parser.add_argument('author')
    parser.add_argument('source')
    parser.add_argument('difficulty', required=True)
    parser.add_argument('length', type=int)
    parser.add_argument('date_added')
    parser.add_argument('start_time')
    parser.add_argument('steps', type=list)

    args = parser.parse_args()

    args['date_added'] = parse_timestamp(args['date_added'])
    args['start_time'] = parse_timestamp(args['start_time'])

    return args


def parse_timestamp(ts):
    """Given a str input, convert it to a datetime object when possible."""
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
        return None


def create_recipe_from_args(args) -> Recipe:
    """Creates a new Recipe object from provided arguments."""
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

    return new_recipe
