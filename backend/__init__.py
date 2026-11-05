"""Initialization file that creates the app and applies our config object."""
import logging
from backend.config import Config
from backend.database import db, migrate
from backend.logging_setup import configure_logging
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from os import path


logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    configure_logging()
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)
    if not breadapp.config.get('SECRET_KEY'):
        raise RuntimeError("SECRET_KEY isn't set; it signs session cookies, so the app won't start without it.")

    # Attach the database and Alembic migrations (via Flask-Migrate) to the app
    db.init_app(breadapp)
    migrate.init_app(breadapp, db, directory=path.join(path.dirname(path.dirname(__file__)), 'migrations'))

    # Credentialed CORS for breadsheet-ui's origins only, so browsers can send cookies (M2's session)
    #   https://flask-cors.readthedocs.io/en/latest/
    CORS(breadapp, resources={r'/api/*': {'origins': breadapp.config['CORS_ORIGINS']}}, supports_credentials=True)

    register_endpoints(Api(breadapp))
    register_v2(breadapp)
    logger.debug("App created")

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
    logger.debug("API v1 endpoints registered")


def register_v2(app: Flask):
    """The /api/v2 blueprint (plain Flask views; see backend/api_v2.py)."""
    from backend.api_v2 import api_v2, register_v2_http_errors
    import backend.identity_routes  # noqa: F401 (registers its routes on the blueprint)
    import backend.recipe_routes_v2  # noqa: F401

    app.register_blueprint(api_v2)
    register_v2_http_errors(app)
    logger.debug("API v2 endpoints registered")
