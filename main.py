"""Define our app using the create_app function in backend/__init__.py"""
# Global logger
from backend.global_logger import logger, local

# External packages
from flask import redirect, request
from flask_restful import Api
from gunicorn import http

# App components
from backend import create_app
from backend.config import Config
from backend.recipe_routes import RecipeCollectionApi, RecipeApi
from backend.replacement_routes import ReplacementCollectionApi
from backend.step_routes import StepApi
from backend.meta_routes import ReadmeApi

breadapp = create_app()
logger.info("Created the Flask breadapp")

api = Api(breadapp)
logger.info("API initialized")

# Define the functional endpoints
api.add_resource(RecipeCollectionApi, '/api/v1/recipes')
api.add_resource(RecipeApi, '/api/v1/recipes/<recipe_id>')
api.add_resource(StepApi, '/api/v1/recipes/<recipe_id>/<step_number>')
api.add_resource(ReplacementCollectionApi,
                 '/api/v1/replacements/<scope>',
                 '/api/v1/replacements/<scope>/<old_value>')

# Define the meta endpoints
api.add_resource(ReadmeApi, '/api/v1/readme')


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
    breadapp.run(host='localhost', port=Config.bound_port, debug=True)
    logger.info(f"Running locally via __main__: http://localhost:{Config.bound_port}")
    print(f"Running locally via __main__: http://localhost:{Config.bound_port}")
