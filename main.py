"""Define our app using the create_app function in backend/__init__.py"""
from global_logger import logger, local
from backend import create_app
from config import Config
from flask import redirect, request

breadapp = create_app()
logger.debug("Executed app = create_app()")


@breadapp.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to my breadsheet.com domain"""
    if 'AppEngine-Google' not in request.user_agent.string:
        logger.debug(f"AppEngine-Google not in {request.user_agent.string}")
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info(f"Requested Host & URL: {request.host} & {request.url}; redirecting to: {Config.domain_url}")
            return redirect(Config.domain_url, code=301)


if __name__ == '__main__' and local:
    breadapp.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")
