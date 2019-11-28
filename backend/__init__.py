"""Initialization file that defines items within the app."""
from config import Config
from flask import Flask


def create_app(config_class=Config):
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)

    return breadapp
