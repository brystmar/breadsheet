"""Defines an object used to configure parameters for our Flask app."""
from backend.global_logger import logger, local
from backend.database import ENGINE_OPTIONS, sqlalchemy_url
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

    SECRET_KEY = environ.get('SECRET_KEY') or '0mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
    logger.debug(f"DOMAIN_URL: {DOMAIN_URL}")
    logger.debug(f"SECRET_KEY: {SECRET_KEY}")

    if SECRET_KEY != environ.get('SECRET_KEY'):
        logger.warning("Error loading SECRET_KEY! Temporarily using a hard-coded key.")

    logger.debug("End of the Config() class.")
