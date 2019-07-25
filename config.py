from global_logger import logger, local
import pytz
from os import path, environ
# from google.cloud import firestore


class Config(object):
    """Define the config parameters for this app."""
    logger.info("Start of the Config() class.")
    logger.debug(f"JSON file exists? {path.isfile('breadsheet-prod.json')}")

    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")

        # GCP Credentials #
        # ...shouldn't be needed anymore

        # AWS credentials
        aws_account_id = environ.get('AWS_ACCOUNT_ID')
        aws_access_key = environ.get('AWS_ACCESS_KEY')
        aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
        aws_user = environ.get('AWS_USER')
        aws_region = environ.get('AWS_REGION')
        aws_arn = environ.get('AWS_ARN')

        # App-related
        SECRET_KEY = environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

    else:
        # AWS credentials
        aws_account_id = environ.get('AWS_ACCOUNT_ID')
        aws_access_key = environ.get('AWS_ACCESS_KEY')
        aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
        aws_user = environ.get('AWS_USER')
        aws_region = environ.get('AWS_REGION')
        aws_arn = environ.get('AWS_ARN')

        # App-related
        SECRET_KEY = environ.get('SECRET_KEY') or '2mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

        logger.debug(f"SECRET_KEY={SECRET_KEY}")
        logger.debug(f"aws_region={aws_region}, user={aws_user}, acct_id={aws_account_id}")

    logger.info("End of the Config() class.")


# TODO: Add support for moment.js
PST = pytz.timezone('US/Pacific')
