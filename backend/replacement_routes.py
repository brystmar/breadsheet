from backend.global_logger import logger
from backend.models import Replacement
from flask import request
from flask_restful import Resource, reqparse
from pynamodb.exceptions import ScanError, DoesNotExist, GetError, QueryError, PutError, PynamoDBException
import json


class ReplacementCollectionApi(Resource):

    def get(self, scope='all') -> json:
        """Returns a collection of all replacements for Paprika-compliant markup."""
        logger.debug(f"Request: {request}")

        try:
            # Determine what to return
            if scope == 'all':
                items = Replacement.scan()
            elif scope in ('ingredients', 'directions'):
                items = Replacement.query(scope)
            else:
                return {'message': 'Error', 'data': f'Invalid scope: {scope}'}, 404

        except ScanError as e:
            error_msg = f"Scope {scope} not found."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except QueryError as e:
            error_msg = f"Scope {scope} not found."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        except BaseException as e:
            error_msg = f"Error searching for scope {scope}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        output = []
        for i in items:
            output.append(i.to_dict())

        logger.debug(f"End of ReplacementCollectionApi.get({scope})")
        return {'message': 'Success', 'data': output}, 200

    def put(self, scope, old_value) -> json:
        """Add or update a replacement record."""
        logger.debug(f"Request: {request}")

        if scope not in ('all', 'ingredients', 'directions'):
            error_msg = f"Invalid scope: {scope}."
            logger.debug(f"{error_msg}")
            return {'message': 'Validation Error', 'data': error_msg}, 422

        # Retrieve the record
        try:
            rep_to_update = Replacement.get(hash_key=scope, range_key=old_value)
            exists = True
            logger.debug(f"Found the requested Replacement record to update: "
                         f"{rep_to_update.__repr__()}")
        except (GetError, DoesNotExist):
            rep_to_update = Replacement()
            exists = False
            logger.debug(f"Requested record does not exist: hash_key={scope}, "
                         f"range_key={old_value}.  Must be a new entry.")

        # Load the provided JSON
        data = json.loads(request.data.decode())
        logger.debug(f"Data submitted: {data}")

        if not exists:
            try:
                rep_to_update = Replacement(scope=scope, old=old_value, new=data['new'])
            except PynamoDBException as e:
                error_msg = f"Error adding scope: {scope}, old: {old_value}, new: {data['new']}."
                logger.debug(f"{error_msg}\n{e}")
                return {'message': 'Error', 'data': error_msg}, 500
        else:
            rep_to_update.scope = scope
            rep_to_update.old = old_value
            rep_to_update.new = data['new']

        try:
            rep_to_update.save()
            logger.debug(f"End of ReplacementCollectionApi.put({scope}, {old_value})")
            if exists:
                return {'message': 'Success', 'data': 'Replacement record updated.'}, 200
            else:
                return {'message': 'Created', 'data': 'Replacement record created.'}, 201

        except PutError as e:
            error_msg = f"Error updating scope: {scope}, old: {old_value}, new: {data['new']}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
