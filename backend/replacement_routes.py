from backend.global_logger import logger
from backend.database import db
from backend.models import Replacement
from flask import request
from flask_restful import Resource
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


def get_replacement(scope, old_value) -> Replacement | None:
    return db.session.scalar(select(Replacement).filter_by(scope=scope, old=old_value))


class ReplacementCollectionApi(Resource):
    """
    Endpoints:  /api/v1/replacements/all,
                /api/v1/replacements/<scope>,
                /api/v1/replacements/<scope>/<old_value>
    """

    def get(self, scope='all') -> dict:
        """Returns a collection of all replacements for Paprika-compliant markup."""
        logger.debug(f"Request: {request}")

        # Determine what to return; within a scope, replacements are sorted by `old` in byte order
        query = select(Replacement).order_by(Replacement.scope, Replacement.old)
        if scope in ['ingredients', 'directions']:
            query = query.filter_by(scope=scope)
        elif scope != 'all':
            return {'message': 'Error', 'data': f'Invalid scope: {scope}'}, 404

        try:
            items = db.session.scalars(query).all()

        except SQLAlchemyError as e:
            error_msg = f"Error searching for scope {scope}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 404

        ingredients = [i.to_dict() for i in items if i.scope == 'ingredients']
        directions = [i.to_dict() for i in items if i.scope == 'directions']

        output = {}
        if ingredients:
            output['ingredients'] = ingredients
        if directions:
            output['directions'] = directions

        logger.debug(f"End of ReplacementCollectionApi.get({scope})")
        return {'message': 'Success', 'data': output}, 200

    def put(self, scope, old_value) -> dict:
        """Add or update a replacement record."""
        logger.debug(f"Request: {request}")

        if scope not in ('all', 'ingredients', 'directions'):
            error_msg = f"Invalid scope: {scope}."
            logger.debug(f"{error_msg}")
            return {'message': 'Validation Error', 'data': error_msg}, 422

        # Load the provided JSON
        data = request.get_json(force=True)
        logger.debug(f"Data submitted: {data}")

        try:
            # Retrieve the record
            rep_to_update = get_replacement(scope, old_value)
            exists = rep_to_update is not None

            if not exists:
                # A new record takes its scope and old value from the body, as v1 always has
                logger.debug(f"Requested record does not exist: scope={scope}, old={old_value}.  "
                             f"Must be a new entry.")
                try:
                    rep_to_update = Replacement(scope=data['scope'], old=data['old'], new=data['new'])
                except (KeyError, TypeError) as e:
                    error_msg = f"Error adding scope: {scope}, old: {old_value}, new: {data.get('new')}."
                    logger.debug(f"{error_msg}\n{e}")
                    return {'message': 'Error', 'data': error_msg}, 500
                db.session.add(rep_to_update)
            else:
                logger.debug(f"Found the requested Replacement record to update: {rep_to_update}")
                rep_to_update.new = data['new']

            db.session.commit()
            logger.debug(f"End of ReplacementCollectionApi.put({scope}, {old_value})")
            if exists:
                return {'message': 'Success', 'data': 'Replacement record updated.'}, 200
            else:
                return {'message': 'Created', 'data': 'Replacement record created.'}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error updating scope: {scope}, old: {old_value}, new: {data.get('new')}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500

    def delete(self, scope, old_value) -> dict:
        """Removes the specified entry."""
        logger.debug(f"Request: {request}")

        if not scope or not old_value:
            error_msg = f"Invalid request: must provide values for scope & old."
            logger.debug(error_msg)
            return {'message': 'Error', 'data': error_msg}, 400

        try:
            item = get_replacement(scope, old_value)
        except SQLAlchemyError as e:
            logger.debug(f"Error {e} retrieving Replacement w/scope: {scope}, old: {old_value}")
            item = None

        if item is None:
            return {'message': 'Error',
                    'data': f"Cannot find Replacement w/scope: {scope}, old: {old_value}"}, 404

        try:
            footprint = f"{item}"
            logger.debug(f"Attempting to delete Replacement {footprint}")
            db.session.delete(item)
            db.session.commit()
            logger.info(f"{footprint} deleted successfully.")
            logger.debug(f"End of ReplacementCollectionApi.DELETE")
            return {'message': 'Success', 'data': f'{footprint} deleted successfully.'}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Error attempting to delete recipe {item}."
            logger.debug(f"{error_msg}\n{e}")
            return {'message': 'Error', 'data': error_msg}, 500
