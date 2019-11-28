from main import logger, breadapp
from flask import request
from flask_restful import Resource
from os import path
import json
import markdown


class DocumentationApi(Resource):
    def get(self) -> json:
        """Returns the API documentation, formatted in html."""
        logger.debug(f"Request: {request}")

        try:
            # Open the README file
            with open(path.dirname(breadapp.root_path) + '/API_Documentation.md', 'r') as markdown_file:
                # Read the file
                content = markdown_file.read()

                # Convert to HTML
                output = markdown.markdown(content)
                return {'message': 'Success', 'data': output}, 200

        except BaseException as e:
            error_msg = f"Error attempting to retrieve or compile the API documentation: {e}.)"
            logger.debug(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500


class ReadmeApi(Resource):
    def get(self) -> json:
        """Returns the README file for this project, formatted in html."""
        logger.debug(f"Request: {request}")

        try:
            # Open the README file
            with open(path.dirname(breadapp.root_path) + '/README.md', 'r') as markdown_readme:
                # Read the file
                content = markdown_readme.read()

                # Convert to HTML
                output = markdown.markdown(content)
                return {'message': 'Success', 'data': output}, 200

        except BaseException as e:
            error_msg = f"Error attempting to retrieve or compile the README file: {e}.)"
            logger.debug(error_msg)
            return {'message': 'Error', 'data': error_msg}, 500
