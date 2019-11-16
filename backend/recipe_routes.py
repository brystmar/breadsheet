"""Defines the API endpoints that the front end will consume."""
from main import logger, breadapp
from backend.functions import generate_new_id
from backend.models import Recipe
from datetime import datetime, timedelta
from flask import request, send_from_directory, redirect, url_for
from flask_restful import Resource, reqparse
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
        return {'message': 'Success', 'data': output}, 200

    def post(self):
        """Add a new recipe."""
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        # TODO: Replace with a different parsing package (ex: marshmallow) since RequestParser
        #  will be deprecated: https://flask-restful.readthedocs.io/en/latest/reqparse.html
        parser = reqparse.RequestParser(bundle_errors=True)

        parser.add_argument('id')  # any id value provided will be ignored
        parser.add_argument('name', required=True)
        parser.add_argument('author')
        parser.add_argument('source')
        parser.add_argument('difficulty')
        parser.add_argument('length', type=int)
        parser.add_argument('date_added')  # any date_added value provided is ignored
        parser.add_argument('start_time')
        parser.add_argument('steps', type=list)

        args = parser.parse_args()

        # Initialize a recipe object
        new_recipe = Recipe(id=generate_new_id(),
                            name=args['name'],
                            author=args['author'],
                            source=args['source'],
                            difficulty=args['difficulty'],
                            length=args['length'],
                            date_added=datetime.utcnow(),
                            start_time=args['start_time'],
                            steps=args['steps'] if args['steps'] else []
                            )

        new_recipe.update_length()

        # Write this new recipe to the db
        logger.info(f"Writing new recipe {new_recipe.__repr__()} to the database.")
        response = new_recipe.save()

        logger.debug("End of add_recipe()")
        return {'message': 'Success', 'data': response}, 201


class RecipeApi(Resource):
    def get(self, recipe_id) -> json:
        """Return a single recipe."""
        logger.debug(f"Request: {request}.")
        print(self.__repr__())

        # Retrieve the recipe from the database
        recipe = Recipe.get(recipe_id)
        logger.debug(f"Recipe retrieved: {recipe.__repr__()})")

        recipe.update_length()

        logger.debug(f"End of GET /recipe/{recipe_id}")
        return {'message': 'Success', 'data': recipe.to_dict()}, 200

    def put(self, args) -> json:
        """Update a recipe."""
        logger.debug(f"Request: {request}.")
        logger.debug(f"Args provided: {request.args}.")
        logger.debug(f"Args provided (view): {request.view_args}.")
        print(self.__repr__())

        # Null handling?

        return {'message': 'Success'}, 201
