# initialization file that defines this package's name as "app"
from flask import Flask
from flask_moment import Moment
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


breadapp = Flask(__name__)
breadapp.config.from_object(Config)
db = SQLAlchemy(breadapp)
migrate = Migrate(breadapp, db)
moment = Moment(breadapp)

from app import routes, models
