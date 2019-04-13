import logging
import os
from google.cloud import firestore

basedir = os.path.abspath(os.path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()
print("local = {}".format(local))


class Config(object):
    # local = True
    # another line for later use
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    logging.debug("local = {}".format(local))
    logging.debug("basedir: {}".format(basedir))
    print("local = {}".format(local))
    print("basedir: {}".format(basedir))

    if local:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(basedir, '.env'))

        SECRET_KEY = os.environ.get('SECRET_KEY') or '1mW7@LN0n32L6ntaj0d8jzsXiAW4mkPL7u5l'
        BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME') or 'local_bucketname'
        db_user = os.environ.get('GCP_CLOUDSQL_USER')
        db_pw = os.environ.get('GCP_CLOUDSQL_PW')
        db_name = os.environ.get('GCP_CLOUDSQL_DBNAME')
        db_ip = os.environ.get('GCP_CLOUDSQL_IP')
        db_port = os.environ.get('GCP_CLOUDSQL_PORT')
        db_instance = os.environ.get('GCP_CLOUDSQL_INSTANCE')

    else:
        fire = firestore.Client()

        from pathlib import Path
        file = Path('breadsheet-prod.json')
        logging.debug("JSON file exists? {}".format(file.is_file()))
        print("JSON file exists? {}".format(file.is_file()))

        # supplying the private (prod) key to explicitly use creds for the default service acct
        fire.from_service_account_json('breadsheet-prod.json')

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

    logging.debug("SQLALCHEMY_DATABASE_URI = {}".format(db_url))
    print("SQLALCHEMY_DATABASE_URI = {}".format(db_url))

    logging.debug("BUCKET_NAME = {}".format(BUCKET_NAME))
    print("BUCKET_NAME = {}".format(BUCKET_NAME))

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False
