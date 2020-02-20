"""Defines an object used to configure parameters for our Flask app."""
from backend.global_logger import logger, local
from os import environ


class Config(object):
    logger.debug("Start of the Config() class.")

    # Apply the environment variables when running locally
    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")

    else:
        # When running in GCP, these are set by the env_variables.yaml file
        pass

    # AWS credentials
    aws_account_id = environ.get('AWS_ACCOUNT_ID')
    aws_access_key = environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
    aws_user = environ.get('AWS_USER')
    aws_region = environ.get('AWS_REGION')
    aws_arn = environ.get('AWS_ARN')

    # App-related
    bound_port = 8000
    domain_url = environ.get('DOMAIN_URL')
    SECRET_KEY = environ.get('SECRET_KEY') or '0mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

    if SECRET_KEY != environ.get('SECRET_KEY'):
        logger.warning("Error loading SECRET_KEY!  Temporarily using a hard-coded key.")

    logger.debug("End of the Config() class.")
