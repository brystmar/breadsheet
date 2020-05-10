"""Define our app using the create_app function in backend/__init__.py"""
# Global logger
from backend.global_logger import logger, local

# External packages
from flask import redirect, request
from flask_cors import CORS
from flask_restful import Api

# App components
from backend import create_app
from backend.config import Config
from backend.recipe_routes import RecipeListApi, RecipeCollectionApi, RecipeApi
from backend.replacement_routes import ReplacementCollectionApi
from backend.meta_routes import ReadmeApi

app = create_app()
logger.info("Created the Flask app")

# Enable CORS for the app; ensure breadsheet-ui is whitelisted
#   https://flask-cors.readthedocs.io/en/latest/
CORS(app, resources={r"/api/*": {"origins": Config.WHITELISTED_ORIGINS}})

api = Api(app)
logger.info("API initialized")

# Define the functional endpoints
api.add_resource(RecipeListApi, '/api/v1/recipe_list')
api.add_resource(RecipeCollectionApi, '/api/v1/recipes')
api.add_resource(RecipeApi, '/api/v1/recipe/<recipe_id>')
api.add_resource(ReplacementCollectionApi,
                 '/api/v1/replacements/<scope>',
                 '/api/v1/replacements/<scope>/<old_value>')

# Define the meta endpoints
api.add_resource(ReadmeApi, '/api/v1/readme')


@app.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to breadsheet.com"""
    if 'AppEngine-Google' not in request.user_agent.string:
        logger.debug(f"AppEngine-Google not in {request.user_agent.string}")
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info(f"Requested Host & URL: {request.host} & {request.url}; "
                        f"redirecting to: {Config.DOMAIN_URL}")
            return redirect(Config.DOMAIN_URL, code=301)


if __name__ == '__main__' and local:
    app.run(host='localhost', port=Config.BOUND_PORT, debug=True)
    logger.info(f"Running locally via __main__: http://localhost:{Config.BOUND_PORT}")
    print(f"Running locally via __main__: http://localhost:{Config.BOUND_PORT}")
