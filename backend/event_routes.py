"""POST /api/v2/events: product events only the browser knows about (breadsheet#34; spec: Usage metrics)."""
import logging
from backend import events
from backend.api_v2 import ApiError, api_v2, json_body
from backend.bake_routes import owned_bake_or_404
from backend.database import db
from backend.recipe_routes_v2 import require_user

logger = logging.getLogger(__name__)


@api_v2.post('/events')
def record_browser_event():
    """
    Record an event from the allow-list (M2: `ics_exported`, for one of the caller's bakes). Anything else
    is refused, so this can't become a channel for arbitrary data.
    """
    user = require_user()
    data = json_body()
    event_type = data.get('type')
    if event_type not in events.BROWSER_EVENTS:
        raise ApiError(400, 'event_type_invalid', f"Event type must be one of: {', '.join(events.BROWSER_EVENTS)}.")
    if not isinstance(data.get('bake_id'), str):
        raise ApiError(400, 'bake_id_invalid', "Send the bake's id.")

    bake = owned_bake_or_404(data['bake_id'], user)
    events.record(event_type, user, recipe_id=bake.recipe_id, bake_id=bake.id)
    db.session.commit()
    return '', 204
