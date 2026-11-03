"""Initialization file that creates the app and applies our config object."""
from backend.global_logger import logger
from backend.config import Config
from backend.database import db, migrate
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from os import path


def create_app(config_class=Config):
    logger.debug(f"Creating app with config")
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)

    # Attach the database and Alembic migrations (via Flask-Migrate) to the app
    db.init_app(breadapp)
    migrate.init_app(breadapp, db, directory=path.join(path.dirname(path.dirname(__file__)), 'migrations'))
    logger.debug("Database initialized")

    # Enable CORS for the app, ensure breadsheet-ui is whitelisted
    #   https://flask-cors.readthedocs.io/en/latest/
    CORS(breadapp, resources=r'/api/*')

    register_endpoints(Api(breadapp))
    logger.debug(f"App created: {breadapp.name}")

    return breadapp


def register_endpoints(api: Api):
    """Define the functional and meta endpoints."""
    from backend.recipe_routes import RecipeCollectionApi, RecipeApi
    from backend.replacement_routes import ReplacementCollectionApi
    from backend.meta_routes import ReadmeApi

    api.add_resource(RecipeCollectionApi, '/api/v1/recipes')
    api.add_resource(RecipeApi, '/api/v1/recipe/<recipe_id>')
    api.add_resource(ReplacementCollectionApi,
                     '/api/v1/replacements/<scope>',
                     '/api/v1/replacements/<scope>/<old_value>')

    api.add_resource(ReadmeApi, '/api/v1/readme')
    logger.info("API endpoints initialized")
