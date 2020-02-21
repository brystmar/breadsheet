from backend.global_logger import logger
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
            with open(path.curdir + '/README.md', 'r') as markdown_readme:
                # Read the file
                content = markdown_readme.read()
                logger.debug("Read the README file")

                # Convert to HTML
                output = markdown.markdown(content)
                logger.debug("Converted the README file")
                return {'message': 'Success', 'data': output}, 200

        except FileNotFoundError as e:
            error_msg = f"File not found."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except ValueError as e:
            error_msg = f"Error attempting to compile the README file.)"
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
