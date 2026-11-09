"""
Product events for usage metrics (breadsheet#34; spec: Usage metrics). Routes call `record()` as things
happen, inside the request's own transaction, so an event exists exactly when its change was committed.
Pseudonymous by design: a user id, never an IP address, user agent, or free text.
"""
import re
from backend.database import db
from backend.models import Event
from flask import g, has_request_context, request

# What the server records as it happens
USER_REGISTERED = 'user_registered'
SIGNED_IN = 'signed_in'
RECIPE_CREATED = 'recipe_created'
RECIPE_COPIED = 'recipe_copied'          # recipe_id: the recipe that was copied (most-copied metrics)
RECIPE_PUBLISHED = 'recipe_published'
RECIPE_UNPUBLISHED = 'recipe_unpublished'
RECIPE_DELETED = 'recipe_deleted'
BAKE_STARTED = 'bake_started'
BAKE_COMPLETED = 'bake_completed'        # the owner finished it early with Complete
BAKE_CANCELED = 'bake_canceled'
STEP_COMPLETED = 'step_completed'        # value: seconds after the step's scheduled time (negative when early)
STEP_SKIPPED = 'step_skipped'
KEY_RESET = 'key_reset'                  # user: whose key an admin reset (breadsheet#87)

# What only the browser knows about; POST /api/v2/events takes these and nothing else
ICS_EXPORTED = 'ics_exported'            # bake_id: the bake whose schedule was downloaded
BROWSER_EVENTS = (ICS_EXPORTED,)

MAX_AGENT_NAME = 40


def agent_name(value: str | None) -> str | None:
    """The agent's self-reported name, reduced to a short plain label (letters, digits, spaces, . _ -)."""
    if not value:
        return None
    cleaned = re.sub(r'[^A-Za-z0-9 ._-]', '', value).strip()[:MAX_AGENT_NAME].strip()
    return cleaned or None


def request_client() -> tuple[str, str | None]:
    """Who made this request: ('agent', name) for agent tool calls (X-Breadsheet-Via: agent), ('ha', None) for
    other calls with a Home Assistant device token, else ('web', None)."""
    if not has_request_context():
        return 'web', None
    if request.headers.get('X-Breadsheet-Via', '').strip().lower() == 'agent':
        return 'agent', agent_name(request.headers.get('X-Breadsheet-Agent'))
    return ('ha', None) if g.get('connection') is not None else ('web', None)


def record(event_type: str, user=None, recipe_id=None, bake_id=None, value: int | None = None) -> Event:
    """Adds an event to the current transaction; it's saved when the request commits."""
    client, agent = request_client()
    event = Event(type=event_type, user=user, recipe_id=recipe_id,
                  bake_id=bake_id, value=value, client=client, agent_name=agent)
    db.session.add(event)
    return event


def seconds_late(scheduled_at, done_at) -> int | None:
    """How many whole seconds after its scheduled time a step was checked off (negative when early)."""
    if scheduled_at is None or done_at is None:
        return None
    return round((done_at - scheduled_at).total_seconds())
