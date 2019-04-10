import logging
import os
from google.cloud import firestore

basedir = os.path.abspath(os.path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()
print("local = {}".format(local))

if local:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(basedir, '.env'))
else:
    fire = firestore.Client()
    firecreds = fire.collection('environment_vars').document('prod').get()


class Config(object):
    hail_mary = False
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    logging.debug("local = {}".format(local))
    logging.debug("basedir: {}".format(basedir))
    print("local = {}".format(local))
    print("basedir: {}".format(basedir))

    if local:
        SECRET_KEY = os.environ.get('SECRET_KEY')
        BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME')
        db_user = os.environ.get('GCP_CLOUDSQL_USER')
        db_pw = os.environ.get('GCP_CLOUDSQL_PW')
        db_name = os.environ.get('GCP_CLOUDSQL_DBNAME')
        db_ip = os.environ.get('GCP_CLOUDSQL_IP')
        db_port = os.environ.get('GCP_CLOUDSQL_PORT')
        db_instance = os.environ.get('GCP_CLOUDSQL_INSTANCE')
    else:
        SECRET_KEY = firecreds._data['SECRET_KEY']
        BUCKET_NAME = firecreds._data['GCP_BUCKET_NAME']
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

    if hail_mary:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'breaddb.db')

    logging.debug("SQLALCHEMY_DATABASE_URI = {}".format(SQLALCHEMY_DATABASE_URI))
    print("SQLALCHEMY_DATABASE_URI = {}".format(SQLALCHEMY_DATABASE_URI))

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False
