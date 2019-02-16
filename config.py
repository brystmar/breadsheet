import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # prefer secret keys set at the environment level, providing an alternative if that doesn't exist
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # use the environment's db url; if missing, use a local sqlite file
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'breadsheet.db')

    # should SQLAlchemy send a notification to the app every time an object changes?
    SQLALCHEMY_TRACK_MODIFICATIONS = False
