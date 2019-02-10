# initialization file that defines this package's name as "app"
from flask import Flask

app = Flask(__name__)

from app import routes