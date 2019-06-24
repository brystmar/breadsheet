from global_logger import glogger, local
import pytz
from os import path, environ
# from google.cloud import firestore

logger = glogger


class Config(object):
    """Define the config parameters for this app."""
    logger.info("Start of the Config() class.")

    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")

        # GCP Credentials #
        # ...shouldn't be needed anymore

        # AWS Credentials #
        aws_account_id = environ.get('AWS_ACCOUNT_ID')
        aws_access_key_id = environ.get('AWS_ACCESS_KEY')
        aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
        aws_user = environ.get('AWS_USER')
        aws_region = environ.get('AWS_REGION')
        aws_arn = environ.get('AWS_ARN')

        SECRET_KEY = environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

        # from google.cloud import firestore
        # logging to stdout in the cloud is automatically routed to a useful monitoring tool
        logger.debug(f"JSON file exists? {path.isfile('breadsheet-prod.json')}")

        # supply the private key to explicitly use creds for the default service acct
        # fire = firestore.Client().from_service_account_json('breadsheet-prod.json')

    else:
        from google.cloud import firestore
        # logging to stdout in the cloud is automatically routed to a useful monitoring tool
        logger.debug(f"JSON file exists? {path.isfile('breadsheet-prod.json')}")

        # supply the private key to explicitly use creds for the default service acct
        fire = firestore.Client().from_service_account_json('breadsheet-prod.json')
        fire_credentials = fire.collection('environment_vars').document('prod').get()

        # GCP Credentials #
        # ...shouldn't be needed anymore

        # AWS Credentials #
        aws_account_id = fire_credentials._data['AWS_ACCOUNT_ID']
        aws_access_key_id = fire_credentials._data['AWS_ACCESS_KEY']
        aws_secret_access_key = fire_credentials._data['AWS_SECRET_ACCESS_KEY']
        aws_user = fire_credentials._data['AWS_USER']
        aws_region = fire_credentials._data['AWS_REGION']
        aws_arn = fire_credentials._data['AWS_ARN']

        SECRET_KEY = fire_credentials._data['SECRET_KEY'] or '2mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

    logger.info("End of the Config() class.")


# TODO: Add support for moment.js
PST = pytz.timezone('US/Pacific')
