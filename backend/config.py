"""Defines an object used to configure parameters for our Flask app."""
from backend.global_logger import logger, local
from backend.database import ENGINE_OPTIONS, sqlalchemy_url
from datetime import timedelta
from os import environ


class Config(object):
    logger.debug("Start of the Config() class.")

    # Apply the environment variables when running locally
    if local:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Local .env variables applied.")

    else:
        # When running in GCP, these are loaded from the env_variables.yaml file when the app loads
        pass

    # Neon Postgres; locally these point at the `dev` branch
    # The app uses the pooled URL; Alembic migrations use the unpooled (direct) URL, since
    #   PgBouncer's transaction mode can leak session state between connections
    DATABASE_URL = environ.get('DATABASE_URL')
    DATABASE_URL_UNPOOLED = environ.get('DATABASE_URL_UNPOOLED')
    SQLALCHEMY_DATABASE_URI = sqlalchemy_url(DATABASE_URL)
    SQLALCHEMY_ENGINE_OPTIONS = ENGINE_OPTIONS
    MIGRATIONS_DATABASE_URI = sqlalchemy_url(DATABASE_URL_UNPOOLED)

    # App-related
    BOUND_PORT = environ.get('BOUND_PORT')
    DOMAIN_URL = environ.get('DOMAIN_URL')

    # Credentialed CORS: only these origins may call /api/*, and wildcards are never allowed
    CORS_ORIGINS = ['https://breadsheet.com', 'https://www.breadsheet.com']
    if local:
        # The Vite dev server (npm start)
        CORS_ORIGINS += ['http://localhost:3000', 'http://127.0.0.1:3000']

    # Signs the session cookie: anyone who knows it can sign in as any user. Each environment has its
    #   own value (.env locally, env_variables.yaml in production), and create_app() refuses to start
    #   without one. Never log it.
    SECRET_KEY = environ.get('SECRET_KEY')

    # Browser sessions (spec: Identity and ownership). Host-only on api.breadsheet.com, which is
    #   same-site with breadsheet.com, so the UI's credentialed fetches send it.
    SESSION_COOKIE_NAME = 'breadsheet_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = not local  # the Vite dev server calls the API over plain http
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SESSION_REFRESH_EACH_REQUEST = True

    logger.debug(f"DOMAIN_URL: {DOMAIN_URL}")
    logger.debug("End of the Config() class.")
