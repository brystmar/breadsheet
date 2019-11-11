"""Define our app using the create_app function in backend/__init__.py"""
from global_logger import logger, local
from backend import create_app
from config import Config
from flask import redirect, request, send_from_directory
from flask_restful import Resource, Api
from os import path

breadapp = create_app()
logger.info("Created the Flask breadapp")

api = Api(breadapp)
logger.info("Initialized the API")


@breadapp.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to my breadsheet.com domain"""
    if 'AppEngine-Google' not in request.user_agent.string:
        logger.debug(f"AppEngine-Google not in {request.user_agent.string}")
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info(f"Requested Host & URL: {request.host} & {request.url}; redirecting to: {Config.domain_url}")
            return redirect(Config.domain_url, code=301)


@breadapp.route('/favicon')
def favicon():
    logger.info("Favicon was requested!! :D")
    return send_from_directory(path.join(breadapp.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__' and local:
    breadapp.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")

# Import the API routes
# from backend import recipe_routes, replacement_routes
from backend import core_routes
from backend.recipe_routes import RecipeCollectionApi, RecipeApi
from backend.replacement_routes import ReplacementCollectionApi, ReplacementApi
from backend.step_routes import StepApi

# Define the endpoints
api.add_resource(RecipeCollectionApi, '/recipes')
api.add_resource(RecipeApi, '/recipe/<recipe_id>/')
api.add_resource(StepApi, '/recipe/<recipe_id>/<step_number>')
api.add_resource(ReplacementCollectionApi, '/replacements/<scope>')
api.add_resource(ReplacementApi, '/replacement')
