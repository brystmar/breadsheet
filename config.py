import logging
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    logging.debug("basedir: {}".format(basedir))
    print("basedir: {}".format(basedir))

    # prefer secret keys set at the environment level, providing an alternative if that doesn't exist
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    logging.debug("sk: {}".format(SECRET_KEY))
    print("sk: {}".format(SECRET_KEY))

    db_user = os.environ.get('GCP_CLOUDSQL_USER')
    db_pw = os.environ.get('GCP_CLOUDSQL_PW')
    db_name = os.environ.get('GCP_CLOUDSQL_DBNAME')
    db_ip = os.environ.get('GCP_CLOUDSQL_IP')
    db_port = os.environ.get('GCP_CLOUDSQL_PORT')
    db_instance = os.environ.get('GCP_CLOUDSQL_INSTANCE')

    db_url = 'postgres+psycopg2://{db_user}:{db_pw}'.format(db_user=db_user, db_pw=db_pw)
    db_url += '@/{db_name}?host=/cloudsql/{db_instance}'.format(db_name=db_name, db_instance=db_instance)
    logging.debug("db_url: {}".format(db_url))
    print("db_url: {}".format(db_url))
    # db_url += '/.s.PGSQL.5432'

    # use the environment's db url; if missing, use a local sqlite file
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'breaddb.db')
    # SQLALCHEMY_DATABASE_URI = db_url
    logging.debug("SQLALCHEMY_DATABASE_URI: {}".format(SQLALCHEMY_DATABASE_URI))
    print("SQLALCHEMY_DATABASE_URI: {}".format(SQLALCHEMY_DATABASE_URI))

    # silence the madness
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # gcp bucket name
    BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME') or None
    logging.debug("bucket name: {}".format(BUCKET_NAME))
    print("bucket name: {}".format(BUCKET_NAME))
