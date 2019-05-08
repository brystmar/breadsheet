# import logging as logging_util
from os import path, environ
from google.cloud import firestore

basedir = path.abspath(path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()
print("local = {}".format(local))
print("__file__ = {}".format(__file__))

# initialize logging
# log_dir = 'logs' if local else 'tmp'
# log_file = '{dir}/syslog.log'.format(dir=log_dir)
# logging_util.basicConfig(filename=log_file, level=logging_util.DEBUG, datefmt='%H:%M:%S',
#                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger_config = logging_util.getLogger(__name__)
# logger_config.info("Logging initialized from the /config.py file")


class Config(object):
    # local = True
    # another line for later use
    # logger_config.debug("local = {}".format(local))
    # logger_config.debug("basedir: {}".format(basedir))
    print("local = {}".format(local))
    print("basedir: {}".format(basedir))

    if local:
        from dotenv import load_dotenv
        load_dotenv(path.join(basedir, '.env'))

        # logger_config.debug("Readme file exists? {}".format(path.isfile('README.md')))
        print("Readme file exists? {}".format(path.isfile('README.md')))

        SECRET_KEY = environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
        BUCKET_NAME = environ.get('GCP_BUCKET_NAME') or 'local_bucketname'
        db_user = environ.get('GCP_CLOUDSQL_USER')
        db_pw = environ.get('GCP_CLOUDSQL_PW')
        db_name = environ.get('GCP_CLOUDSQL_DBNAME')
        db_ip = environ.get('GCP_CLOUDSQL_IP')
        db_port = environ.get('GCP_CLOUDSQL_PORT')
        db_instance = environ.get('GCP_CLOUDSQL_INSTANCE')

    else:
        # logger_config.debug("JSON file exists? {}".format(path.isfile('breadsheet-prod.json')))
        print("JSON file exists? {}".format(path.isfile('breadsheet-prod.json')))

        # supplying the private (prod) key to explicitly use creds for the default service acct
        fire = firestore.Client().from_service_account_json('breadsheet-prod.json')

        # this call should work now
        firecreds = fire.collection('environment_vars').document('prod').get()
        print("Firecreds GCP bucket: {}".format(firecreds._data['GCP_BUCKET_NAME']))

        SECRET_KEY = firecreds._data['SECRET_KEY'] or '2mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
        BUCKET_NAME = firecreds._data['GCP_BUCKET_NAME'] or 'fire_fail_bucketname'
        db_user = firecreds._data['GCP_CLOUDSQL_USER']
        db_pw = firecreds._data['GCP_CLOUDSQL_PW']
        db_name = firecreds._data['GCP_CLOUDSQL_DBNAME']
        db_ip = firecreds._data['GCP_CLOUDSQL_IP']
        db_port = firecreds._data['GCP_CLOUDSQL_PORT']
        db_instance = firecreds._data['GCP_CLOUDSQL_INSTANCE']

    db_url = 'postgres+psycopg2://{db_user}:{db_pw}'.format(db_user=db_user, db_pw=db_pw)
    db_url += '@/{db_name}?host=/cloudsql/{db_instance}'.format(db_name=db_name, db_instance=db_instance)
    # db_url += '/.s.PGSQL.5432'

    # use the environment's db url; if missing, use a local sqlite file
    SQLALCHEMY_DATABASE_URI = db_url
    # SQLALCHEMY_DATABASE_URI = 'postgres+psycopg2://USER:PW@/breadsheet?host=/cloudsql/breadsheet:us-west1:breadsheet'

    # logger_config.debug("SQLALCHEMY_DATABASE_URI = {}".format(db_url))
    print("SQLALCHEMY_DATABASE_URI = {}".format(db_url))

    # logger_config.debug("BUCKET_NAME = {}".format(BUCKET_NAME))
    print("BUCKET_NAME = {}".format(BUCKET_NAME))

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False
