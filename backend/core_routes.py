from main import logger, breadapp, api
from flask import request
from os import path
import markdown


@breadapp.route('/')
@breadapp.route('/api')
def index():
    """Returns the API documentation."""
    logger.debug(f"Request: {request}")

    # Open the README file
    with open(path.dirname(breadapp.root_path) + '/API_Documentation.md', 'r') as markdown_file:
        # Read the file
        content = markdown_file.read()

        # Convert to HTML
        return markdown.markdown(content)


@breadapp.route('/readme')
def get_readme():
    """Returns the README file for this project."""
    logger.debug(f"Request: {request}")

    # Open the README file
    with open(path.dirname(breadapp.root_path) + '/README.md', 'r') as markdown_readme:
        # Read the file
        content = markdown_readme.read()

        # Convert to HTML
        return markdown.markdown(content)
