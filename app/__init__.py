# initialization file that defines the app as breadapp
from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
# from logging.handlers import RotatingFileHandler
import logging

bootstrap = Bootstrap()
db = SQLAlchemy()
moment = Moment()


def create_app(config_class=Config):
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)

    bootstrap.init_app(breadapp)
    db.init_app(breadapp)
    moment.init_app(breadapp)

    from app.errors import bp as errors_bp
    breadapp.register_blueprint(errors_bp)

    from app.main import bp as main_bp
    breadapp.register_blueprint(main_bp)

    from app.convert import bp as convert_bp
    breadapp.register_blueprint(convert_bp)

    # log errors when running in production mode
    """if not breadapp.debug and not breadapp.testing:
        pass
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        breadapp.logger.addHandler(file_handler)

        breadapp.logger.setLevel(logging.INFO)
        breadapp.logger.info('Breadsheet startup')"""

    return breadapp


from app import models
