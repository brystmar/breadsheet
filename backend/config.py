"""Defines an object used to configure parameters for our Flask app."""
from backend.global_logger import logger, local
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

    # AWS credentials
    AWS_ACCOUNT_ID = environ.get('AWS_ACCOUNT_ID')
    AWS_ACCESS_KEY = environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_USER = environ.get('AWS_USER')
    AWS_REGION = environ.get('AWS_REGION')
    AWS_ARN = environ.get('AWS_ARN')
    logger.debug(f"Running in AWS Region: {AWS_REGION}")

    # App-related
    BOUND_PORT = environ.get('BOUND_PORT')
    DOMAIN_URL = environ.get('DOMAIN_URL')
    WHITELISTED_ORIGIN = environ.get('WHITELISTED_ORIGIN')
    WHITELISTED_ORIGINS = environ.get('WHITELISTED_ORIGINS')
    SECRET_KEY = environ.get('SECRET_KEY') or '0mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
    logger.debug(f"DOMAIN_URL: {DOMAIN_URL}")
    logger.debug(f"SECRET_KEY: {SECRET_KEY}")

    if SECRET_KEY != environ.get('SECRET_KEY'):
        logger.warning("Error loading SECRET_KEY! Temporarily using a hard-coded key.")

    logger.debug("End of the Config() class.")
