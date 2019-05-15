# initialization file that defines items within the app
from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from global_logger import glogger
import logging

logger = glogger
logger.setLevel(logging.DEBUG)

bootstrap = Bootstrap()
db = SQLAlchemy()
moment = Moment()


def create_app(config_class=Config):
    logger.debug("Starting the create_app() function in /app/__init__.py")

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

    logger.debug("End of the create_app() function in /app/__init__.py")
    return app


from app import models
