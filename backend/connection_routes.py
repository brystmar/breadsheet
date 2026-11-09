"""Pairing Home Assistant and managing its connections: /api/v2/pairing-codes, /devices, /connections (breadsheet#27)."""
import logging
from backend import poll_cache, rate_limits
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.devices import (CODE_LIFETIME, DEVICE_SCOPES, clean_label, hash_secret, new_device_token,
                             new_pairing_code, normalized_code)
from backend.models import Connection, PairingCode, utc_now
from backend.recipe_routes_v2 import require_user
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from uuid import UUID

logger = logging.getLogger(__name__)

CODE_INVALID = "That pairing code is wrong or has expired. Get a new one from your profile on breadsheet.com."


@api_v2.post('/pairing-codes')
def issue_pairing_code():
    """A new pairing code for the signed-in browser's user, good for ten minutes. Any earlier unused code stops working."""
    user = require_user()
    for _ in range(3):  # a collision among live codes is vanishingly rare; try again if it happens
        code = new_pairing_code()
        db.session.execute(delete(PairingCode).where(PairingCode.user_id == user.id, PairingCode.used_at.is_(None)))
        pairing = PairingCode(code_hash=hash_secret(normalized_code(code)), user_id=user.id,
                              expires_at=utc_now() + CODE_LIFETIME)
        db.session.add(pairing)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            continue
        logger.info("User %s issued a pairing code", user.id)
        return {'code': code, 'expires_at': pairing.expires_at.isoformat()}, 201
    raise RuntimeError("Couldn't issue a unique pairing code")


@api_v2.post('/devices')
def pair_device():
    """
    Home Assistant's config flow exchanges a pairing code for a device token, shown once here and never again.
    The code works once, within ten minutes. Failed attempts are rate limited per network. The response names the
    user, since a token can't call GET /session: HA keys its config entry on the user id, so pairing the same
    account twice, or re-pairing with another account's code, can be caught.
    """
    rate_limits.enforce(rate_limits.PAIRING_FAILURES, "Too many pairing attempts from this network. Wait a bit and try again.")
    data = json_body()
    code = normalized_code(data.get('code'))
    now = utc_now()
    pairing = db.session.scalar(
        select(PairingCode).where(PairingCode.code_hash == hash_secret(code)).with_for_update()) if code else None
    if pairing is None or pairing.used_at is not None or pairing.expires_at <= now:
        db.session.rollback()
        rate_limits.record(rate_limits.PAIRING_FAILURES)
        raise ApiError(400, 'pairing_code_invalid', CODE_INVALID)

    token = new_device_token()
    pairing.used_at = now
    connection = Connection(user_id=pairing.user_id, label=clean_label(data.get('label')),
                            scopes=list(DEVICE_SCOPES), token_hash=hash_secret(token))
    db.session.add(connection)
    db.session.commit()
    logger.info("User %s paired connection %s", pairing.user_id, connection.id)
    return {'token': token, 'connection': connection.to_v2_dict(), 'user': pairing.user.to_dict()}, 201


@api_v2.get('/connections')
def list_connections():
    """The signed-in user's paired Home Assistant instances, newest first. Revoked ones are left out."""
    user = require_user()
    connections = db.session.scalars(select(Connection).where(Connection.user_id == user.id,
                                                              Connection.revoked_at.is_(None))
                                     .order_by(Connection.created_at.desc(), Connection.id))
    return {'connections': [connection.to_v2_dict() for connection in connections]}, 200


@api_v2.delete('/connections/<connection_id>')
def revoke_connection(connection_id):
    """Revoke a connection: its token stops working at once, along with every agent calling through it."""
    user = require_user()
    try:
        connection = db.session.scalar(select(Connection).where(Connection.id == UUID(connection_id),
                                                                Connection.user_id == user.id))
    except ValueError:
        connection = None
    if connection is None or connection.revoked_at is not None:
        raise ApiError(404, 'not_found', "That connection doesn't exist.")
    connection.revoked_at = utc_now()
    db.session.commit()
    poll_cache.forget_token(connection.token_hash)  # so idle polls stop answering for it too
    logger.info("User %s revoked connection %s", user.id, connection.id)
    return '', 204
