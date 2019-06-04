from global_logger import glogger, local
import logging

from os import path, environ, getcwd
# from google.cloud import firestore

# test_client = firestore.Client
logger = glogger
logger.setLevel(logging.DEBUG)


class Config(object):
    """Set the config parameters for this app."""
    logger.info("Start of the Config() class.")

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")

        # GCP Credentials #
        BUCKET_NAME = environ.get('GCP_BUCKET_NAME') or 'local_fail_bucket_name'
        db_user = environ.get('GCP_CLOUDSQL_USER')
        db_pw = environ.get('GCP_CLOUDSQL_PW')
        db_name = environ.get('GCP_CLOUDSQL_DBNAME')
        db_ip = environ.get('GCP_CLOUDSQL_IP')
        db_port = environ.get('GCP_CLOUDSQL_PORT')
        db_instance = environ.get('GCP_CLOUDSQL_INSTANCE')
        db_url = environ.get('GCP_CLOUDSQL_DATABASE_URI')

        # AWS Credentials #
        aws_access_key_id = environ.get('AWS_ACCESS_KEY')
        aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')
        aws_user = environ.get('AWS_USER')
        aws_region = environ.get('AWS_REGION')
        aws_arn = environ.get('AWS_ARN')

        SECRET_KEY = environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

        # from google.cloud import firestore
        # logging to stdout in the cloud is automatically routed to a useful monitoring tool
        logger.debug("JSON file exists? {}".format(path.isfile('breadsheet-prod.json')))

        # supply the private key to explicitly use creds for the default service acct
        # fire = firestore.Client().from_service_account_json('breadsheet-prod.json')
        # logger.debug("Fire_credentials GCP bucket: {}".format(BUCKET_NAME))

    else:
        from google.cloud import firestore
        # logging to stdout in the cloud is automatically routed to a useful monitoring tool
        logger.debug("JSON file exists? {}".format(path.isfile('breadsheet-prod.json')))

        # supply the private key to explicitly use creds for the default service acct
        fire = firestore.Client().from_service_account_json('breadsheet-prod.json')
        fire_credentials = fire.collection('environment_vars').document('prod').get()

        # GCP Credentials #
        BUCKET_NAME = fire_credentials._data['GCP_BUCKET_NAME'] or 'fire_fail_bucket_name'
        db_user = fire_credentials._data['GCP_CLOUDSQL_USER']
        db_pw = fire_credentials._data['GCP_CLOUDSQL_PW']
        db_name = fire_credentials._data['GCP_CLOUDSQL_DBNAME']
        db_ip = fire_credentials._data['GCP_CLOUDSQL_IP']
        db_port = fire_credentials._data['GCP_CLOUDSQL_PORT']
        db_instance = fire_credentials._data['GCP_CLOUDSQL_INSTANCE']
        db_url = fire_credentials._data['GCP_CLOUDSQL_DATABASE_URI']

        logger.info("Fire_credentials GCP bucket: {}".format(BUCKET_NAME))
        logger.info("DB IP from fire_credentials: {}".format(db_ip))

        # AWS Credentials #
        aws_access_key_id = fire_credentials._data['AWS_ACCESS_KEY']
        aws_secret_access_key = fire_credentials._data['AWS_SECRET_ACCESS_KEY']
        aws_user = fire_credentials._data['AWS_USER']
        aws_region = fire_credentials._data['AWS_REGION']
        aws_arn = fire_credentials._data['AWS_ARN']

        SECRET_KEY = fire_credentials._data['SECRET_KEY'] or '2mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'

    SQLALCHEMY_DATABASE_URI = db_url
    # SQLALCHEMY_DATABASE_URI = 'postgres+psycopg2://USER:PW@/breadsheet?host=/cloudsql/trivialib:us-west2:trivialib'

    logger.debug("SQLALCHEMY_DATABASE_URI: {}".format(db_url))
    logger.info("End of the Config() class.")
