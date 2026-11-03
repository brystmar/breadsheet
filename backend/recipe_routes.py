"""Defines recipe-related endpoints for the front end to consume."""
from backend.global_logger import logger
from backend.database import db
from backend.models import Recipe, utc_now
from flask import request
from flask_restful import Resource
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID


def get_recipe(recipe_id) -> Recipe | None:
    """Returns the recipe with this id, or None. Ids that aren't UUIDs (e.g. legacy DynamoDB ids) don't exist."""
    try:
        return db.session.get(Recipe, UUID(str(recipe_id)))
    except ValueError:
        return None


class RecipeCollectionApi(Resource):
    """Endpoint: /api/v1/recipes"""

    def get(self) -> dict:
        """Return a collection of all recipes. Read-only: never writes to the db."""
        logger.debug(f"Request: {request}.")

        try:
            # Grab all recipes from the db, sorted by date_added (the homepage order)
            recipes = db.session.scalars(select(Recipe).order_by(Recipe.date_added, Recipe.id)).all()

            # Convert each to a dictionary, compile into a list
            output = [recipe.to_dict(dates_as_epoch=True) for recipe in recipes]

            logger.debug(f"End of RecipeCollectionApi.GET")
            return {'message': 'Success', 'data': output}, 200
        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve or compile recipe list."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def post(self) -> dict:
        """Add a new recipe based on the submitted JSON."""
        logger.debug(f"Request: {request}.")

        # Ensure there's a body to accompany this request
        data = request.get_json(force=True)
        if data is None:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400

        logger.debug(f"Data submitted: {data}")

        # Create a new Recipe from the provided data; the server assigns its id
        try:
            new_recipe = Recipe()
            new_recipe.update_from_v1(data)
            new_recipe.last_modified = new_recipe.date_added
            logger.debug(f"Recipe object created: {new_recipe}.")

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            error_msg = f"Other error in parsing args."
            logger.debug(f"{error_msg}\n{e}.")
            return {'message': 'Error', 'data': error_msg}, 500

        # Write this new recipe to the db
        try:
            logger.debug(f"Attempting to save recipe...")
            db.session.add(new_recipe)
            db.session.commit()
            logger.info(f"Successfully saved new recipe {new_recipe}.")

            logger.debug("End of RecipeCollectionApi.POST")
            return {'message': 'Created', 'data': new_recipe.to_dict(dates_as_epoch=False)}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to save new recipe."
            logger.debug(f"{error_msg}\n{e}.")
            return {'message': 'Error', 'data': error_msg}, 500


class RecipeApi(Resource):
    """Endpoint: /api/v1/recipe/<recipe_id>"""

    def get(self, recipe_id) -> dict:
        """Return a single recipe."""
        logger.debug(f"Request: {request}, for id: {recipe_id}.")

        # Retrieve the recipe from the database
        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug(f"Recipe {recipe_id} not found.")
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

            logger.debug(f"Recipe retrieved: {recipe})")
            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=True)}, 200
        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def put(self, recipe_id) -> dict:
        """
        Update an existing recipe using data from the request.
        Returns a copy of the new recipe.
        """
        logger.debug(f"Request: {request}.")

        # Ensure there's a body to accompany this request
        data = request.get_json(force=True)
        if data is None:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400

        logger.debug(f"Data submitted: {data}")

        # Ensure the /<recipe_id> provided to the endpoint matches the recipe_id in the body.
        if str(recipe_id) != str(data.get('id')):
            error_msg = f"/recipe_id provided to the endpoint ({recipe_id}) " \
                        f"doesn't match the id from the body ({data.get('id')})."
            logger.debug(f"{error_msg}")
            return {'message': 'Error', 'data': error_msg}, 400

        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug(f"Recipe {recipe_id} not found.")
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

            # Apply the provided data to the recipe
            try:
                recipe.update_from_v1(data)
                logger.debug(f"Recipe updated from the provided data.")
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                db.session.rollback()
                error_msg = f"Error parsing data into the Recipe model."
                logger.debug(f"{error_msg}\n{e}")
                return {'message': 'Error', 'data': f'{error_msg}\n{e}'}, 500

            # Update the last_modified timestamp and save to the database
            recipe.last_modified = utc_now()
            logger.debug(f"Attempting to save recipe...")
            db.session.commit()
            logger.info(f"Recipe updated: {recipe})")
            logger.debug(f"End of RecipeApi.PUT")
            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=True)}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to save recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, recipe_id) -> dict:
        """Delete the specified recipe."""
        logger.debug(f"Request: {request}.")

        # Retrieve the recipe from the database
        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug(f"Recipe {recipe_id} not found.")
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404
            logger.debug(f"Recipe retrieved: {recipe})")

        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

        # Delete the specified recipe; its steps are removed with it
        try:
            footprint = f"{recipe}"
            logger.debug(f"Attempting to delete recipe {footprint}")
            db.session.delete(recipe)
            db.session.commit()
            logger.info(f"{footprint} deleted successfully.")
            logger.debug(f"End of RecipeApi.DELETE")
            return {'message': 'Success', 'data': f'{footprint} deleted successfully.'}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to delete recipe {recipe}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
