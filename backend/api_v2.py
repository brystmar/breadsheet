"""
The /api/v2 blueprint and its conventions, shared by every v2 endpoint:

- Errors return JSON with a stable `code` and a plain-language `message` that says what to do next.
- State-changing requests must send `Content-Type: application/json`, which forces a CORS preflight;
  with SameSite=Lax cookies and the CORS allow-list, that's the CSRF protection.
- Responses are never cached, since they're per-user.
- A database outage returns 503 `service_unavailable` with Retry-After.

Plain Flask views, not Flask-RESTful (unmaintained); v1 keeps Flask-RESTful.
"""
from backend.database import db
from backend.global_logger import logger
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException

api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

STATE_CHANGING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
DB_RETRY_AFTER_SECONDS = 30


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def error_response(status: int, code: str, message: str, headers: dict | None = None):
    response = jsonify({'code': code, 'message': message})
    response.status_code = status
    response.headers.update(headers or {})
    response.headers['Cache-Control'] = 'no-store'
    return response


def json_body() -> dict:
    """The request's JSON object, or a 400 error."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, 'body_invalid', "Send a JSON object in the request body.")
    return data


@api_v2.before_request
def require_json_for_state_changes():
    if request.method in STATE_CHANGING_METHODS and not request.is_json:
        raise ApiError(415, 'json_required', "Send this request with Content-Type: application/json.")


@api_v2.after_request
def never_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@api_v2.errorhandler(ApiError)
def handle_api_error(e: ApiError):
    return error_response(e.status, e.code, e.message, e.headers)


@api_v2.errorhandler(OperationalError)
def handle_database_outage(e: OperationalError):
    logger.error(f"Database unavailable: {e}")
    db.session.rollback()
    return error_response(503, 'service_unavailable',
                          "Breadsheet can't reach its database right now. Try again shortly.",
                          {'Retry-After': str(DB_RETRY_AFTER_SECONDS)})


def register_v2_http_errors(app):
    """JSON bodies for routing errors under /api/v2 (unknown paths and wrong methods), which happen
    before the blueprint is chosen, so the blueprint's own handlers can't catch them."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        if not request.path.startswith(api_v2.url_prefix + '/'):
            return e
        code = {404: 'not_found', 405: 'method_not_allowed'}.get(e.code, 'http_error')
        allowed = getattr(e, 'valid_methods', None)
        return error_response(e.code, code, e.description or e.name,
                              {'Allow': ', '.join(allowed)} if allowed else None)
