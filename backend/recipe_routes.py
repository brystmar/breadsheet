"""
v1 recipe endpoints: read-only, default recipes only.

v1 writes were turned off in breadsheet#28; POST, PUT and DELETE return 405. Default recipes are
managed with the admin key (backend/admin_routes.py).
"""
import logging
from backend.database import db
from backend.models import Recipe
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
