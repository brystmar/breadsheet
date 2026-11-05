"""Entrypoint: App Engine's gunicorn serves `main:app` (see app.yaml); locally, run this file."""
import logging
from backend import create_app
from backend.config import Config
from backend.environment import ON_APP_ENGINE, local
from flask import redirect, request

# Logging, the database, CORS, and the API endpoints are all set up in create_app()
app = create_app()
logger = logging.getLogger(__name__)

# App Engine's legacy bundled services (memcache, for rate limits) need the SDK's WSGI wrapper.
#   Locally, backend/cache.py uses an in-process dict instead.
if ON_APP_ENGINE:
    from google.appengine.api import wrap_wsgi_app
    app.wsgi_app = wrap_wsgi_app(app.wsgi_app)


@app.before_request
def handle_before_request():
    """Redirect breadsheet.appspot.com requests to breadsheet.com"""
    if 'AppEngine-Google' not in request.user_agent.string:
        if 'breadsheet.appspot.com' in request.host.lower():
            logger.info("Redirecting %s to %s", request.host, Config.DOMAIN_URL)
            return redirect(Config.DOMAIN_URL, code=301)
    return None


if __name__ == '__main__' and local:
    logger.info("Running locally at http://127.0.0.1:%s", Config.BOUND_PORT)
    app.run(host='127.0.0.1', port=Config.BOUND_PORT, debug=True)
