# initialization file that defines items within the app
from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
# import logging as logging_util
from os import path


bootstrap = Bootstrap()
db = SQLAlchemy()
moment = Moment()

basedir = path.abspath(path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()


def create_app(config_class=Config):
    # initialize logging
    # log_dir = 'logs' if local else 'tmp'
    # log_file = '{dir}/syslog.log'.format(dir=log_dir)
    # logging_util.basicConfig(filename=log_file, level=logging_util.DEBUG, datefmt='%H:%M:%S',
    #                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # logger = logging_util.getLogger(__name__)
    # logger.info("Logging initialized from the /app/__init__.py file")

    app = Flask(__name__)
    app.config.from_object(config_class)

    bootstrap.init_app(app)
    db.init_app(app)
    moment.init_app(app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.convert import bp as convert_bp
    app.register_blueprint(convert_bp)

    # log errors when running in prod
    """if not app.debug and not app.testing:
        pass
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Breadsheet startup')"""

    return app


from app import models
