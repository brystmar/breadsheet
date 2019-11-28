from main import logger, local
from os import environ


class Config(object):
    """Define the config parameters for this app."""
    logger.debug("Start of the Config() class.")

    # Apply the environment variables when running locally
    # When running in GCP, these are set by the env_variables.yaml file
    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")

    # AWS credentials
    aws_account_id = environ.get('AWS_ACCOUNT_ID')
    aws_access_key = environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
    aws_user = environ.get('AWS_USER')
    aws_region = environ.get('AWS_REGION')
    aws_arn = environ.get('AWS_ARN')

    # App-related
    SECRET_KEY = environ.get('SECRET_KEY') or '0mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
    domain_url = environ.get('DOMAIN_URL')

    logger.debug("End of the Config() class.")
