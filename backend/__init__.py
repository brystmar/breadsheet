"""Initialization file that creates the app and applies our config object."""
from backend.global_logger import logger
from backend.config import Config
from flask import Flask


def create_app(config_class=Config):
    logger.debug(f"Creating app with config")
    breadapp = Flask(__name__)
    breadapp.config.from_object(config_class)
    logger.debug(f"App created: {breadapp.name}")

    return breadapp
