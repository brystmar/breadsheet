"""Defines recipe-related endpoints for the front end to consume."""
import logging
from backend.database import db
from backend.models import Recipe, utc_now
from backend.slugs import unique_default_slug
from flask import request
from flask_restful import Resource
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

logger = logging.getLogger(__name__)


def get_recipe(recipe_id) -> Recipe | None:
    """
    Returns the default recipe with this id, or None. v1 only ever sees default recipes: personal
    recipes (breadsheet#29) don't exist here. Ids that aren't UUIDs (e.g. legacy DynamoDB ids) don't exist.
    """
    try:
        recipe = db.session.get(Recipe, UUID(str(recipe_id)))
    except ValueError:
        return None
    return recipe if recipe is not None and recipe.is_default else None


class RecipeCollectionApi(Resource):
    """Endpoint: /api/v1/recipes"""

    def get(self) -> dict:
        """Return a collection of all recipes. Read-only: never writes to the db."""

        try:
            # Grab all recipes from the db, sorted by date_added (the homepage order)
            # Default recipes only: personal recipes never appear in v1
            recipes = db.session.scalars(select(Recipe)
                                         .where(Recipe.owner_id.is_(None))
                                         .order_by(Recipe.date_added, Recipe.id)).all()

            # Convert each to a dictionary, compile into a list
            output = [recipe.to_dict(dates_as_epoch=True) for recipe in recipes]

            return {'message': 'Success', 'data': output}, 200
        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve or compile recipe list."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500

    def post(self) -> dict:
        """Add a new recipe based on the submitted JSON."""

        # Ensure there's a body to accompany this request
        data = request.get_json(force=True)
        if data is None:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400


        # Create a new Recipe from the provided data; the server assigns its id
        try:
            new_recipe = Recipe()
            new_recipe.update_from_v1(data)
            new_recipe.last_modified = new_recipe.date_added

            # v1 creates default recipes; their slug is set once and never changes
            new_recipe.slug = unique_default_slug(db.session, new_recipe.name)

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            error_msg = f"Other error in parsing args."
            logger.warning("%s %s", error_msg, e)
            return {'message': 'Error', 'data': error_msg}, 500

        # Write this new recipe to the db
        try:
            db.session.add(new_recipe)
            db.session.commit()
            logger.info("Created recipe %s", new_recipe.id)
            return {'message': 'Created', 'data': new_recipe.to_dict(dates_as_epoch=False)}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to save new recipe."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500


class RecipeApi(Resource):
    """Endpoint: /api/v1/recipe/<recipe_id>"""

    def get(self, recipe_id) -> dict:
        """Return a single recipe."""

        # Retrieve the recipe from the database
        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug("Recipe %s not found", recipe_id)
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=True)}, 200
        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500

    def put(self, recipe_id) -> dict:
        """
        Update an existing recipe using data from the request.
        Returns a copy of the new recipe.
        """

        # Ensure there's a body to accompany this request
        data = request.get_json(force=True)
        if data is None:
            return {'message': 'Error', 'data': 'POST request must contain a body.'}, 400


        # Ensure the /<recipe_id> provided to the endpoint matches the recipe_id in the body.
        if str(recipe_id) != str(data.get('id')):
            error_msg = f"/recipe_id provided to the endpoint ({recipe_id}) " \
                        f"doesn't match the id from the body ({data.get('id')})."
            logger.debug(error_msg)
            return {'message': 'Error', 'data': error_msg}, 400

        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug("Recipe %s not found", recipe_id)
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

            # Apply the provided data to the recipe
            try:
                recipe.update_from_v1(data)
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                db.session.rollback()
                error_msg = f"Error parsing data into the Recipe model."
                logger.warning("%s %s", error_msg, e)
                return {'message': 'Error', 'data': f'{error_msg}\n{e}'}, 500

            # Update the last_modified timestamp and save to the database
            recipe.last_modified = utc_now()
            db.session.commit()
            logger.info("Updated recipe %s", recipe.id)
            return {'message': 'Success', 'data': recipe.to_dict(dates_as_epoch=True)}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to save recipe {recipe_id}."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, recipe_id) -> dict:
        """Delete the specified recipe."""

        # Retrieve the recipe from the database
        try:
            recipe = get_recipe(recipe_id)
            if recipe is None:
                logger.debug("Recipe %s not found", recipe_id)
                return {'message': 'Not Found', 'data': f'Recipe {recipe_id} not found.'}, 404

        except SQLAlchemyError as e:
            error_msg = f"Error attempting to retrieve recipe {recipe_id}."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500

        # Delete the specified recipe; its steps are removed with it
        try:
            footprint = f"{recipe}"
            db.session.delete(recipe)
            db.session.commit()
            logger.info("Deleted %s", footprint)
            return {'message': 'Success', 'data': f'{footprint} deleted successfully.'}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to delete recipe {recipe}."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500
