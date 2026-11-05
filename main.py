"""Define our app using the create_app function in backend/__init__.py"""
# Global logger
from backend.global_logger import logger, local

# External packages
from flask import redirect, request

# App components (CORS, the database, and the API endpoints are set up in create_app)
from backend import create_app
from backend.config import Config

app = create_app()
logger.info("Created the Flask app")

# App Engine's legacy bundled services (memcache, for rate limits) need the SDK's WSGI wrapper.
#   Locally, backend/cache.py uses an in-process dict instead.
from backend.cache import ON_APP_ENGINE
if ON_APP_ENGINE:
    from google.appengine.api import wrap_wsgi_app
    app.wsgi_app = wrap_wsgi_app(app.wsgi_app)


@app.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to breadsheet.com"""
    if 'AppEngine-Google' not in request.user_agent.string:
        logger.debug(f"AppEngine-Google not in {request.user_agent.string}")
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info(f"Requested Host & URL: {request.host} & {request.url}; "
                        f"redirecting to: {Config.DOMAIN_URL}")
            return redirect(Config.DOMAIN_URL, code=301)
    return None


if __name__ == '__main__' and local:
    app.run(host='127.0.0.1', port=Config.BOUND_PORT, debug=True)
    logger.info(f"Running locally via __main__: http://127.0.0.1:{Config.BOUND_PORT}")
    print(f"Running locally via __main__: http://127.0.0.1:{Config.BOUND_PORT}")
