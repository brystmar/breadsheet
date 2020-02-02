from main import logger, breadapp
from flask import request
from flask_restful import Resource
from os import path
import json
import markdown


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

        except FileNotFoundError as e:
            error_msg = f"ERRORMSG: File not found."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except ValueError as e:
            error_msg = f"ERRORMSG: Error attempting to compile the README file.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
