"""
v2 bakes (breadsheet#31): start (optionally partway through), read, change, check off, complete, cancel.

- A bake snapshots a recipe's steps (text, note, range, chosen wait, hands-on detail) at start, so
  later recipe edits or deletion never change it. Any recipe the user can see can be baked, except drafts.
- The schedule is anchored to a start or finish time and re-projected on every change (Bake.project).
- Status: not_started until a step is checked off or skipped, in_progress after, completed once every
  step is done, the owner completes or cancels it, or an hour passes after its projected end. `outcome`
  says which (finished, canceled, expired). Expiry is computed on read and written back.
- Starting partway through (`start_at_step`) copies earlier steps as skipped: no time, no alerts.
- Bakes are private: every endpoint is owner-only, and other people get 404.
- Writes lock the bake's row, so simultaneous check-offs can't race.
"""
import logging
from backend.api_v2 import ApiError, api_v2, json_body
from backend.database import db
from backend.models import Bake, BakeStep, User, utc_now
from backend.recipe_routes_v2 import MAX_WAIT_SECONDS, require_user, visible_recipe_or_404
from backend.slugs import is_public_suffix, new_public_suffix
from datetime import datetime, timedelta
from flask import request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

ACTIVE_BAKE_LIMIT = 3
COMPLETED_LIMIT = 50
ANCHOR_TYPES = ('start', 'finish')
ALERT_MODES = ('simple', 'fancy')
MAX_IDEMPOTENCY_KEY = 200
CLOCK_SKEW = timedelta(minutes=5)


## Parsing ##

def parse_time(value) -> datetime | None:
    """An ISO 8601 timestamp with a UTC offset (or Z); None if it isn't one."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def valid_time_zone(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def check_alert_mode(value, problems: dict) -> str | None:
    if value is None:
        return None
    if value not in ALERT_MODES:
        problems['alert_mode'] = f"Must be one of: {', '.join(ALERT_MODES)}."
        return None
    if value == 'fancy':
        raise ApiError(409, 'fancy_requires_ha', "Fancy alerts need Home Assistant, which isn't available yet. "
                                                 "Use simple alerts for now.")
    return value


def parse_anchor(data: dict, problems: dict, required: bool) -> tuple[str | None, datetime | None]:
    anchor_type, anchor_time = data.get('anchor_type'), data.get('anchor_time')
    if anchor_type is None and anchor_time is None and not required:
        return None, None
    if anchor_type not in ANCHOR_TYPES:
        problems['anchor_type'] = f"Must be one of: {', '.join(ANCHOR_TYPES)}."
    parsed = parse_time(anchor_time)
    if parsed is None:
        problems['anchor_time'] = "Must be an ISO 8601 time with a UTC offset, e.g. 2026-11-07T08:00:00-08:00."
    return anchor_type, parsed


def parse_waits(value, positions: set[int], problems: dict) -> dict[int, int]:
    """`waits`: [{position, wait_chosen}] overrides. Outside the step's range is fine (flagged); 0-30 days isn't."""
    if value is None:
        return {}
    if not isinstance(value, list):
        problems['waits'] = "Must be a list of {position, wait_chosen}."
        return {}
    waits, out_of_range = {}, {}
    for i, item in enumerate(value):
        field = f'waits[{i}]'
        position = item.get('position') if isinstance(item, dict) else None
        wait = item.get('wait_chosen') if isinstance(item, dict) else None
        if isinstance(position, bool) or position not in positions:
            problems[field] = "Must name one of the recipe's step positions."
        elif position in waits:
            problems[field] = "That step is listed twice."
        elif isinstance(wait, bool) or not isinstance(wait, int) or not 0 <= wait <= MAX_WAIT_SECONDS:
            out_of_range[field] = "Must be a whole number of seconds, from 0 to 30 days."
        else:
            waits[position] = wait
    if out_of_range and not problems:
        first = next(iter(out_of_range.values()))
        raise ApiError(400, 'wait_out_of_range', f"Check the waits: {first}", fields=out_of_range)
    problems.update(out_of_range)
    return waits


def checked_completed_at(value, bake: Bake, now: datetime, required: bool = True) -> datetime:
    """When the user did it: not more than five minutes ahead, and not before the bake started."""
    if value is None and not required:
        return now
    completed_at = parse_time(value)
    if completed_at is None:
        message = "Send completed_at: the ISO 8601 time the step was done, with a UTC offset."
    elif completed_at > now + CLOCK_SKEW:
        message = "completed_at is in the future. Send the time it was actually done."
    elif completed_at < bake.started_at:
        message = "completed_at is before this bake started."
    else:
        return completed_at
    raise ApiError(400, 'completed_at_invalid', message)


def raise_if(problems: dict):
    if problems:
        first = next(iter(problems.values()))
        raise ApiError(400, 'bake_invalid', f"Check the bake: {first}", fields=problems)


## Helpers ##

def owned_bake_or_404(bake_id, user: User, lock: bool = False) -> Bake:
    try:
        query = select(Bake).where(Bake.id == UUID(str(bake_id)), Bake.user_id == user.id)
    except ValueError:
        query = None
    bake = db.session.scalar(query.with_for_update() if lock else query) if query is not None else None
    if bake is None:
        raise ApiError(404, 'not_found', "That bake doesn't exist.")
    return bake


def refreshed(bakes: list[Bake]) -> list[Bake]:
    """Completes any bake whose projected end has passed, and saves that (written back lazily, on read)."""
    now = utc_now()
    if any([bake.refresh_status(now) for bake in bakes]):
        db.session.commit()
    return bakes


def respond(bake: Bake, status: int = 200):
    return {'bake': bake.to_v2_dict()}, status


def refuse_if_over(bake: Bake):
    if bake.projected_end <= utc_now():
        raise ApiError(400, 'bake_already_over', "That schedule would already be over. Pick a later start or finish.")


def refuse_if_completed(bake: Bake):
    if bake.status == 'completed':
        raise ApiError(409, 'bake_completed', "This bake is finished, so it can't change. Start a new one.")


## Endpoints ##

@api_v2.post('/bakes')
def start_bake():
    """Start a bake from any recipe the user can see. A repeated Idempotency-Key returns the original bake."""
    user = require_user()

    key = request.headers.get('Idempotency-Key')
    if key is not None:
        key = key.strip()
        if not key or len(key) > MAX_IDEMPOTENCY_KEY:
            raise ApiError(400, 'idempotency_key_invalid', f"Idempotency-Key must be 1 to {MAX_IDEMPOTENCY_KEY} characters.")
        existing = db.session.scalar(select(Bake).where(Bake.user_id == user.id, Bake.idempotency_key == key))
        if existing is not None:
            return respond(refreshed([existing])[0])

    data = json_body()
    problems = {}
    if not isinstance(data.get('recipe_id'), str):
        raise_if({'recipe_id': "Choose a recipe."})
    recipe = visible_recipe_or_404(data['recipe_id'], user)
    if recipe.is_draft:
        raise ApiError(409, 'recipe_is_draft', "Drafts can't be baked. Save it as a finished recipe first.")
    if not recipe.steps:
        raise ApiError(400, 'recipe_has_no_steps', "That recipe has no steps to bake.")

    alert_mode = check_alert_mode(data.get('alert_mode'), problems) or 'simple'
    anchor_type, anchor_time = parse_anchor(data, problems, required=True)
    time_zone = data.get('time_zone')
    if not valid_time_zone(time_zone):
        problems['time_zone'] = "Must be an IANA time zone, e.g. America/Los_Angeles."
    positions = [step.position for step in recipe.steps]
    waits = parse_waits(data.get('waits'), set(positions), problems)
    start_at_step = data.get('start_at_step', positions[0])
    if isinstance(start_at_step, bool) or start_at_step not in positions:
        problems['start_at_step'] = "Must name one of the recipe's step positions."
    raise_if(problems)

    active = [bake for bake in refreshed(list(db.session.scalars(
        select(Bake).where(Bake.user_id == user.id, Bake.status != 'completed')))) if bake.is_active]
    if len(active) >= ACTIVE_BAKE_LIMIT:
        raise ApiError(409, 'bake_limit_reached', f"You can have up to {ACTIVE_BAKE_LIMIT} bakes going at once. "
                                                  "Finish or cancel one first.")

    bake = Bake(user_id=user.id, recipe_id=recipe.id, name_snapshot=recipe.name,
                public_suffix=new_public_suffix(db.session, Bake), anchor_type=anchor_type, anchor_time=anchor_time,
                time_zone=time_zone, alert_mode=alert_mode, status='not_started', created_via='web',
                idempotency_key=key, started_at=utc_now())
    bake.steps = [BakeStep(position=step.position, text_snapshot=step.text, note_snapshot=step.note or None,
                           wait_min=step.wait_min, wait_max=step.wait_max,
                           wait_chosen=waits.get(step.position, step.default_wait),
                           active_seconds=step.active_seconds, needs_presence=step.needs_presence,
                           skipped=step.position < start_at_step)
                  for step in recipe.steps]
    bake.project()
    refuse_if_over(bake)
    bake.refresh_status(bake.started_at)  # starting partway through is already in progress

    db.session.add(bake)
    try:
        db.session.commit()
    except IntegrityError:
        # The same Idempotency-Key raced in from another request: return the bake that won
        db.session.rollback()
        existing = db.session.scalar(select(Bake).where(Bake.user_id == user.id, Bake.idempotency_key == key)) \
            if key else None
        if existing is None:
            raise
        return respond(existing)

    logger.info("User %s started bake %s from recipe %s", user.id, bake.id, recipe.id)
    return respond(bake, 201)


@api_v2.get('/bakes')
def list_bakes():
    """The caller's active bakes (default), or their newest completed ones (`status=completed`), with schedules."""
    user = require_user()
    status = request.args.get('status', 'active')
    if status not in ('active', 'completed'):
        raise ApiError(400, 'status_invalid', "Pick a status: active or completed.")

    active = refreshed(list(db.session.scalars(
        select(Bake).where(Bake.user_id == user.id, Bake.status != 'completed').order_by(Bake.started_at, Bake.id))))
    if status == 'active':
        bakes = [bake for bake in active if bake.is_active]
    else:
        bakes = db.session.scalars(select(Bake).where(Bake.user_id == user.id, Bake.status == 'completed')
                                   .order_by(Bake.completed_at.desc(), Bake.id).limit(COMPLETED_LIMIT))
    return {'bakes': [bake.to_v2_dict() for bake in bakes]}, 200


@api_v2.get('/bakes/<bake_id>')
def get_bake(bake_id):
    return respond(refreshed([owned_bake_or_404(bake_id, require_user())])[0])


@api_v2.get('/bakes/by-suffix/<suffix>')
def bake_by_suffix(suffix):
    """Resolve a bake URL (/bakes/<suffix>) for its owner, with the bake's internal id."""
    user = require_user()
    bake = db.session.scalar(select(Bake).where(Bake.public_suffix == suffix, Bake.user_id == user.id)) \
        if is_public_suffix(suffix) else None
    if bake is None:
        raise ApiError(404, 'not_found', "That bake doesn't exist.")
    return respond(refreshed([bake])[0])


@api_v2.patch('/bakes/<bake_id>')
def update_bake(bake_id):
    """Change the anchor (before the first check-off), chosen waits, or alert mode; re-projects the schedule."""
    user = require_user()
    bake = owned_bake_or_404(bake_id, user, lock=True)
    bake.refresh_status(utc_now())
    refuse_if_completed(bake)

    data = json_body()
    problems = {}
    alert_mode = check_alert_mode(data.get('alert_mode'), problems)
    anchor_type, anchor_time = parse_anchor(data, problems, required=False)
    waits = parse_waits(data.get('waits'), {step.position for step in bake.steps}, problems)
    raise_if(problems)
    if alert_mode is None and anchor_type is None and not waits:
        raise ApiError(400, 'body_invalid', "Send anchor_type and anchor_time, waits, or alert_mode to change.")

    if anchor_type is not None:
        if any(step.completed_at for step in bake.steps):
            raise ApiError(409, 'bake_in_progress', "The schedule follows your check-offs once a bake is under way, "
                                                    "so its start or finish can't change. Adjust the waits instead.")
        bake.anchor_type, bake.anchor_time = anchor_type, anchor_time
    for step in bake.steps:
        if step.position in waits:
            step.wait_chosen = waits[step.position]
    if alert_mode is not None:
        bake.alert_mode = alert_mode

    bake.project()
    refuse_if_over(bake)
    db.session.commit()
    logger.info("User %s updated bake %s", user.id, bake.id)
    return respond(bake)


@api_v2.post('/bakes/<bake_id>/complete')
def finish_bake(bake_id):
    """
    Finish a bake now (the UI confirms first if steps remain): every remaining step is checked off at
    `completed_at` (default now), taking the baker's word for it. Outcome: finished. Repeating changes
    nothing; a canceled or expired bake can't be finished.
    """
    user = require_user()
    bake = owned_bake_or_404(bake_id, user, lock=True)
    now = utc_now()
    bake.refresh_status(now)
    if bake.outcome == 'finished':
        db.session.commit()
        return respond(bake)
    refuse_if_completed(bake)

    completed_at = checked_completed_at(json_body().get('completed_at'), bake, now, required=False)
    for step in bake.steps:
        if not step.is_done:
            step.completed_at = completed_at
    bake.project()
    bake.end('finished', completed_at)
    db.session.commit()
    logger.info("User %s completed bake %s", user.id, bake.id)
    return respond(bake)


@api_v2.post('/bakes/<bake_id>/cancel')
def cancel_bake(bake_id):
    """End a bake without finishing it: steps not yet done stay unchecked. Outcome: canceled. Repeating, or
    canceling a bake that's already completed, changes nothing."""
    user = require_user()
    bake = owned_bake_or_404(bake_id, user, lock=True)
    now = utc_now()
    bake.refresh_status(now)
    if bake.status != 'completed':
        bake.end('canceled', now)
        logger.info("User %s canceled bake %s", user.id, bake.id)
    db.session.commit()
    return respond(bake)


@api_v2.post('/bakes/<bake_id>/steps/<int:position>/complete')
def complete_step(bake_id, position):
    """
    Check off a step at the client's `completed_at`. The first write wins: repeating (or checking off a
    skipped step) returns the bake unchanged. Early and out-of-order check-offs are fine; every later step
    re-projects.
    """
    user = require_user()
    bake = owned_bake_or_404(bake_id, user, lock=True)
    step = next((s for s in bake.steps if s.position == position), None)
    if step is None:
        raise ApiError(404, 'not_found', "That step doesn't exist in this bake.")
    if step.is_done:  # already checked off, or skipped: the first write wins
        db.session.commit()  # releases the lock
        return respond(bake)

    now = utc_now()
    bake.refresh_status(now)
    refuse_if_completed(bake)

    step.completed_at = checked_completed_at(json_body().get('completed_at'), bake, now)
    bake.project()
    bake.refresh_status(now)
    db.session.commit()
    logger.info("User %s checked off step %s of bake %s", user.id, position, bake.id)
    return respond(bake)
