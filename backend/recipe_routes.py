"""Defines recipe-related endpoints for the front end to consume."""
from backend.global_logger import logger
from backend.models import Recipe
from flask import request
from flask_restful import Resource
from pynamodb.exceptions import PynamoDBException
import json


class RecipeListApi(Resource):
    """Endpoint: /api/v1/recipe_list"""

    def get(self) -> json:
        """Return a skinny list of all recipes."""
        logger.debug(f"GET request: {request}.")

        try:
            # Grab all recipes from the db, sort by id
            recipes = Recipe.scan()
            output = []

            # Strip away unnecessary fields
            for recipe in recipes:
                output.append({"id": recipe.id, "name": recipe.name})
                pass

            output = sorted(output, key=lambda r: r['id'])

            logger.debug(f"End of RecipeListApi.GET")
            return {'message': 'Success', 'data': output}, 200
        except PynamoDBException as e:
            error_msg = f"Error attempting to retrieve or compile recipe list."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500


class RecipeCollectionApi(Resource):
    """Endpoint: /api/v1/recipes"""

    def get(self) -> json:
        """Return a collection of all recipes."""
        logger.debug(f"Request: {request}.")

        try:
            # Grab all recipes from the db, then sort by id
            recipes = Recipe.scan()
            recipes = sorted(recipes, key=lambda r: r.date_added)

            # Convert each to a dictionary, compile into a list
            output = []
            for recipe in recipes:
                recipe.update_length()
                output.append(recipe.to_dict(dates_as_epoch=True))

            logger.debug(f"End of RecipeCollectionApi.GET")
            return {'message': 'Success', 'data': output}, 200
        except PynamoDBException as e:
            error_msg = f"Error attempting to retrieve or compile recipe list."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def post(self) -> json:
        """Add a new recipe based on the submitted JSON."""
        logger.debug(f"Request: {request}.")

        # Ensure there's a body to accompany this request
        if not request.data:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400

        # Parse the provided JSON
        try:
            data = json.loads(request.data.decode())
            logger.debug(f"Data submitted: {data}")

        except json.JSONDecodeError as e:
            error_msg = f"Error attempting to decode the provided JSON."
            logger.debug(f"{error_msg},\n{request.data.__str__()},\n{e}")
            return {'message': 'Error', 'data': error_msg + f"\n{request.data.__str__()}"}, 400
        except BaseException as e:
            error_msg = f"Unknown error attempting to decode JSON."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 400

        # Create a new Recipe from the provided data
        try:
            new_recipe = Recipe(**data)
            new_recipe.update_length()
            logger.debug(f"Recipe object created: {new_recipe}.")

        except PynamoDBException as e:
            error_msg = f"Error attempting to create new recipe from: {data}."
            logger.debug(f"{error_msg}\nError: {e}.")
            return {'message': 'Error', 'data': error_msg}, 500
        except BaseException as e:
            error_msg = f"Other error in parsing args."
            logger.debug(f"{error_msg}\n{e}.")
            return {'message': 'Error', 'data': error_msg}, 500

        # Write this new recipe to the db
        try:
            logger.debug(f"Attempting to save recipe...")
            new_recipe.save()
            logger.info(f"Successfully saved new recipe {new_recipe}.")

            logger.debug("End of RecipeCollectionApi.POST")
            return {'message': 'Created', 'data': new_recipe.to_dict(dates_as_epoch=False)}, 201

        except PynamoDBException as e:
            error_msg = f"Error attempting to save new recipe."
            logger.debug(f"{error_msg}\n{new_recipe}: {e}.")
            return {'message': 'Error', 'data': error_msg}, 500


class RecipeApi(Resource):
    """Endpoint: /api/v1/recipe/<recipe_id>"""

    def get(self, recipe_id) -> json:
        """Return a single recipe."""
        logger.debug(f"Request: {request}, for id: {recipe_id}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe.get(recipe_id)
            recipe.update_length()
            logger.debug(f"Recipe retrieved: {recipe})")
            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=True)}, 200
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
        except PynamoDBException as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def put(self, recipe_id) -> json:
        """
        Update an existing recipe using data from the request.
        Returns a copy of the new recipe.
        """
        logger.debug(f"Request: {request}.")

        # Ensure there's a body to accompany this request
        if not request.data:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400

        # Load & decode the provided JSON
        try:
            data = json.loads(request.data.decode())
            logger.debug(f"Data submitted: {data}")

        except json.JSONDecodeError as e:
            error_msg = f"Error attempting to decode the provided JSON."
            logger.debug(f"{error_msg},\n{request.data.__str__()},\n{e}")
            return {'message': 'Error', 'data': error_msg + f"\n{request.data.__str__()}"}, 400
        except BaseException as e:
            error_msg = f"Unknown error attempting to decode JSON."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 400

        # Ensure the /<recipe_id> provided to the endpoint matches the recipe_id in the body.
        if str(recipe_id) != str(data['id']):
            error_msg = f"/recipe_id provided to the endpoint ({recipe_id}) " \
                        f"doesn't match the id from the body ({data['id']})."
            logger.debug(f"{error_msg}")
            return {'message': 'Error', 'data': error_msg}, 400

        # Create a new Recipe instance using the provided data
        # try:
        recipe = Recipe(**data)
        logger.debug(f"Recipe object created.")

        # except PynamoDBException as e:
        #     error_msg = f"Error parsing data into the Recipe model."
        #     logger.debug(f"{error_msg}\n{e}")
        #     return {'message': 'Error', 'data': f'{error_msg}\n{e}'}, 500

        # Save to the database
        try:
            logger.debug(f"Attempting to save recipe...")
            recipe.save()
            logger.info(f"Recipe updated: {recipe})")
            logger.debug(f"End of RecipeApi.PUT")
            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=False)}, 200
        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
        except PynamoDBException as e:
            error_msg = f"Error attempting to save recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, recipe_id) -> json:
        """Delete the selected recipe."""
        logger.debug(f"Request: {request}.")

        # Retrieve the recipe from the database
        try:
            recipe = Recipe().get(recipe_id)
            logger.debug(f"Recipe retrieved: {recipe})")

        except Recipe.DoesNotExist:
            logger.debug(f"Recipe {recipe_id} not found.")
            return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
        except PynamoDBException as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        # Delete the specified recipe
        try:
            footprint = f"{recipe}"
            logger.debug(f"Attempting to delete recipe {footprint}")
            recipe.delete()
            logger.info(f"{footprint} deleted successfully.")
            logger.debug(f"End of RecipeApi.DELETE")
            return {'message': 'Success', 'data': f'{footprint} deleted successfully.'}, 200

        except PynamoDBException as e:
            error_msg = f"Error attempting to delete recipe {recipe}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
