import logging
from flask import request
from flask_restful import Resource
from markdown import markdown
from os import path

logger = logging.getLogger(__name__)


class ReadmeApi(Resource):
    """Endpoint: /api/v1/readme"""

    def get(self) -> dict:
        """Returns the README file for this project, formatted in html."""

        try:
            # Open the README file
            with open(path.curdir + '/README.md', 'r') as markdown_readme:
                # Read the file
                content = markdown_readme.read()

                # Convert to HTML
                output = markdown(content)
                return {'message': 'Success', 'data': output}, 200

        except FileNotFoundError as e:
            error_msg = f"File not found."
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 404

        except ValueError as e:
            error_msg = f"Error attempting to compile the README file.)"
            logger.exception(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500
