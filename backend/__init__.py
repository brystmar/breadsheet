"""Initialization file that creates the app and applies our config object."""
from config import Config
from flask import Flask


def create_app(config_class=Config):
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)

    return breadapp
