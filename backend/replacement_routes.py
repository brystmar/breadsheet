from main import logger
from backend.models import Replacement
from flask import request
from flask_restful import Resource
from pynamodb.exceptions import ScanError, TableDoesNotExist
import json


class ReplacementCollectionApi(Resource):
    def get(self, scope='all'):
        """Returns a collection of all replacements for Paprika-compliant markup."""
        print(self.__repr__())
        logger.debug(f"Request: {request.method}")

        if scope == 'all':
            items = Replacement.scan()
        else:
            items = Replacement.query(scope)

        output = []
        for i in items:
            output.append(i.to_dict())

        logger.debug(f"End of request: {request.method}")
        return output, 200


class ReplacementApi(Resource):
    def put(self):
        print(self.__repr__())
        return f"Support for {request.method} coming soon!", 200


def replacements_verbose() -> json:
    """Returns all replacements data."""
    try:
        reps = Replacement.scan()
        return {
            'Status': '200',
            'Details': {
                'Data': reps.next().dumps(),
                'Message': 'Success!'
            }
        }

    except ScanError as e:
        return {
            'Status': '400',
            'Details': {
                'Error': str(e),
                'ErrorType': ScanError,
                'Message': 'Scan error on the Replacement table.'
            }
        }

    except TableDoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': TableDoesNotExist,
                'Message': 'Replacement table does not exist.'
            }
        }
