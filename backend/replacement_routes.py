from main import logger
from backend.models import Replacement
from flask import request
from flask_restful import Resource, reqparse
from pynamodb.exceptions import ScanError, DoesNotExist, GetError, QueryError, PutError
import json


class ReplacementCollectionApi(Resource):

    def get(self, scope='all'):
        """Returns a collection of all replacements for Paprika-compliant markup."""
        logger.debug(f"Request: {request}")

        try:
            # Determine what to return
            if scope == 'all':
                items = Replacement.scan()
            elif scope in ('ingredients', 'directions'):
                items = Replacement.query(scope)
            else:
                return {
                           'message': 'Not Found',
                           'data':    f'Invalid scope: {scope}'
                       }, 404
        except ScanError as e:
            error_msg = f"Error trying to scan the Replacement table for scope: {scope}.\n{e}."
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500
        except QueryError as e:
            error_msg = f"Error trying to query the Replacement table for scope: {scope}.\n{e}."
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500
        except BaseException as e:
            error_msg = f"Unknown error reading the Replacement table for scope: {scope}.\n{e}."
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500

        output = []
        for i in items:
            output.append(i.to_dict())

        logger.debug(f"End of ReplacementCollectionApi.get({scope})")
        return {
                   'message': 'Success',
                   'data':    output
               }, 200

    def put(self, scope, old_value):
        """Add or update a replacement record."""
        logger.debug(f"Request: {request}")

        if scope not in ('all', 'ingredients', 'directions'):
            logger.debug(f"Invalid scope: {scope}.")
            return {
                       'message': 'Validation Error',
                       'data':    f"Invalid scope: {scope}."
                   }, 422

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

        # Initialize the parser
        parser = reqparse.RequestParser(bundle_errors=True)

        # Specify the arguments provided
        parser.add_argument('new')
        args = parser.parse_args()

        if not exists:
            try:
                rep_to_update = Replacement(scope=scope, old=old_value, new=args['new'])
            except BaseException as e:
                error_msg = f"Error creating a new Replacement entity w/scope: {scope}, " \
                            f"old: {old_value}, new: {args['new']}.\n{e}."
                logger.debug(error_msg)
                return {
                           'message': 'Error',
                           'data':    error_msg
                       }, 500
        else:
            rep_to_update.scope = scope
            rep_to_update.old = old_value
            rep_to_update.new = args['new']

        try:
            rep_to_update.save()
            logger.debug(f"End of ReplacementCollectionApi.put({scope}, {old_value})")
            if exists:
                return {
                           'message': 'Success',
                           'data':    'Replacement record updated successfully.'
                       }, 200
            else:
                return {
                           'message': 'Created',
                           'data':    'Replacement record created successfully.'
                       }, 201
        except PutError as e:
            error_msg = f"Error updating a Replacement entity w/scope: {scope}, " \
                        f"old: {old_value}, new: {args['new']}.\n{e}."
            logger.debug(error_msg)
            return {
                       'message': 'Error',
                       'data':    error_msg
                   }, 500
