"""Define our app using the create_app function in backend/__init__.py"""
from global_logger import logger, local
from backend import create_app
from config import Config
from flask import redirect, request, send_from_directory
from flask_restful import Api
from os import path

breadapp = create_app()
logger.info("Created the Flask breadapp")

api = Api(breadapp)
logger.info("Initialized the API")


@breadapp.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to breadsheet.com"""
    if 'AppEngine-Google' not in request.user_agent.string:
        logger.debug(f"AppEngine-Google not in {request.user_agent.string}")
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info(f"Requested Host & URL: {request.host} & {request.url}; "
                        f"redirecting to: {Config.domain_url}")
            return redirect(Config.domain_url, code=301)


if __name__ == '__main__' and local:
    breadapp.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")

# Import the API routes
from backend import core_routes
from backend.recipe_routes import RecipeCollectionApi, RecipeApi
from backend.replacement_routes import ReplacementCollectionApi
from backend.step_routes import StepApi
from backend.core_routes import DocumentationApi, ReadmeApi

# Define the functional endpoints
api.add_resource(RecipeCollectionApi, '/recipes')
api.add_resource(RecipeApi, '/recipes/<recipe_id>')
api.add_resource(StepApi, '/recipes/<recipe_id>/<step_number>')
api.add_resource(ReplacementCollectionApi,
                 '/replacements/<scope>',
                 '/replacements/<scope>/<old_value>')

# Define the core endpoints
api.add_resource(DocumentationApi, '/', '/api')
api.add_resource(ReadmeApi, '/readme')
