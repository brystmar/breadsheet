from os import path, environ
from global_logger import glogger, local
import logging

logger = glogger
logger.setLevel(logging.INFO)


class Config(object):
    """Set the config parameters for this app."""
    logger.info("Start of the Config() class.")

    if local:
        from env_tools import apply_env
        apply_env()
        logger.info("Applied .env variables using env_tools")
        logger.debug("Readme file exists? {}".format(path.isfile('README.md')))

        SECRET_KEY = environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
        BUCKET_NAME = environ.get('GCP_BUCKET_NAME') or 'local_fail_bucket_name'
        db_user = environ.get('GCP_CLOUDSQL_USER')
        db_pw = environ.get('GCP_CLOUDSQL_PW')
        db_name = environ.get('GCP_CLOUDSQL_DBNAME')
        db_ip = environ.get('GCP_CLOUDSQL_IP')
        db_port = environ.get('GCP_CLOUDSQL_PORT')
        db_instance = environ.get('GCP_CLOUDSQL_INSTANCE')

    else:
        from google.cloud import firestore
        # logging to stdout in the cloud is automatically routed to a useful monitoring tool
        logger.debug("JSON file exists? {}".format(path.isfile('breadsheet-prod.json')))

        # supplying the private (prod) key to explicitly use creds for the default service acct
        fire = firestore.Client().from_service_account_json('breadsheet-prod.json')

        # this call should work now
        fire_credentials = fire.collection('environment_vars').document('prod').get()
        # fire_credentials = fire_credentials._data
        logger.info("Fire_credentials GCP bucket: {}".format(fire_credentials._data['GCP_BUCKET_NAME']))

        SECRET_KEY = fire_credentials._data['SECRET_KEY'] or '2mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
        BUCKET_NAME = fire_credentials._data['GCP_BUCKET_NAME'] or 'fire_fail_bucket_name'
        db_user = fire_credentials._data['GCP_CLOUDSQL_USER']
        db_pw = fire_credentials._data['GCP_CLOUDSQL_PW']
        db_name = fire_credentials._data['GCP_CLOUDSQL_DBNAME']
        db_ip = fire_credentials._data['GCP_CLOUDSQL_IP']
        db_port = fire_credentials._data['GCP_CLOUDSQL_PORT']
        db_instance = fire_credentials._data['GCP_CLOUDSQL_INSTANCE']

        logger.info("DB IP from fire_credentials: {}".format(db_ip))
        logger.info("DB instance from fire_credentials: {}".format(db_instance))

    # set the database URI
    db_url = 'postgres+psycopg2://{u}:{pw}'.format(u=db_user, pw=db_pw)
    db_url += '@/{db}?host=/cloudsql/{i}'.format(db=db_name, i=db_instance)
    # db_url += '/.s.PGSQL.5432'

    SQLALCHEMY_DATABASE_URI = db_url
    # SQLALCHEMY_DATABASE_URI = 'postgres+psycopg2://USER:PW@/breadsheet?host=/cloudsql/trivialib:us-west2:trivialib'

    logger.info("SQLALCHEMY_DATABASE_URI: {}".format(db_url))
    print("print --> SQLALCHEMY_DATABASE_URI: {}".format(db_url))

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    logger.info("End of the Config() class.")
