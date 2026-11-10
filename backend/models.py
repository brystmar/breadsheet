"""SQLAlchemy models: recipes, recipe_steps, and replacements (M1); users, recipe scopes, detail, categories, bakes (M2)."""
from backend.database import db
from datetime import datetime, timedelta, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, UniqueConstraint, Uuid, func
from sqlalchemy import false as sql_false, text as sql_text  # aliased: RecipeStep has a `text` column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid7
from zoneinfo import ZoneInfo


# Scheduling assumes this much hands-on time when a step's active_seconds is unknown (spec: unknown is not zero)
UNKNOWN_HANDS_ON_SECONDS = 10 * 60

# A bake stays active this long past its projected end, so late check-offs still count
BAKE_GRACE = timedelta(hours=1)


def hands_on(active_seconds: int | None, needs_presence: bool | None) -> tuple[int, bool, bool]:
    """
    (hands-on seconds, estimated, needs presence) for scheduling. Unknown is not zero: a null
    active_seconds means 10 minutes, estimated; a null needs_presence means presence is needed.
    """
    estimated = active_seconds is None
    return (UNKNOWN_HANDS_ON_SECONDS if estimated else active_seconds), estimated, needs_presence is not False


def iso(value: datetime | None, zone: str | None = None) -> str | None:
    """An ISO 8601 timestamp in UTC, or in an IANA time zone with its offset."""
    if value is None:
        return None
    return value.astimezone(ZoneInfo(zone) if zone else timezone.utc).isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_v1_datetime(value, fallback: datetime) -> datetime:
    """
    Converts a datetime sent by a v1 client, which uses JavaScript epoch milliseconds.
    Empty values (None, 0, "", "none", "null", "nan") return the fallback, as v1 always has.
    """
    if not value or str(value).strip().lower() in ("none", "null", "nan"):
        return fallback

    if isinstance(value, bool):
        raise ValueError(f"Invalid datetime: {value}")

    if isinstance(value, (int, float)):
        # Convert from JS milliseconds to seconds
        return datetime.fromtimestamp(value / 1000, timezone.utc)

    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class UuidPrimaryKey:
    """
    UUIDv7 primary key: time-ordered, and random enough that ids can't be enumerated.
    Assigned when the object is created, so it's known before the first flush; the server
    default covers rows inserted with raw SQL.
    """
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7, server_default=sql_text("uuidv7()"))

    def __init__(self, **kwargs):
        kwargs.setdefault('id', uuid7())
        super().__init__(**kwargs)


class Recipe(UuidPrimaryKey, db.Model):
    __tablename__ = 'recipes'

    __table_args__ = (
        # Personal recipes (with an owner) have a public suffix; defaults never do
        CheckConstraint("(owner_id IS NULL) = (public_suffix IS NULL)", name="suffix_only_for_personal"),
        UniqueConstraint("public_suffix", name="uq_recipes_public_suffix"),
        # Default slugs are unique among defaults; personal recipes are found by their suffix instead
        Index("uq_recipes_default_slug", "slug", unique=True, postgresql_where=sql_text("owner_id IS NULL")),
        # Only personal recipes can be published (breadsheet#58); the community list reads newest first
        CheckConstraint("owner_id IS NOT NULL OR published_at IS NULL", name="published_only_personal"),
        Index("ix_recipes_published_at", "published_at", postgresql_where=sql_text("published_at IS NOT NULL")),
        # Detail levels and drafts (breadsheet#30): only personal recipes are drafts, and drafts are never published
        CheckConstraint("detail_level IN ('simple', 'detailed')", name="detail_level_valid"),
        CheckConstraint("owner_id IS NOT NULL OR NOT is_draft", name="drafts_only_personal"),
        CheckConstraint("NOT is_draft OR published_at IS NULL", name="drafts_never_published"),
    )

    ## Scope (breadsheet#29) ##
    # The user who owns this personal recipe, or None for a default (admin-owned, read-only for users)
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_recipes_owner_id_users"), index=True)
    owner: Mapped["User | None"] = relationship(lazy="selectin")

    # User-facing URLs: /recipes/<slug> for defaults, /recipes/<slug>-<public_suffix> for personal recipes.
    #   Default slugs never change; a personal recipe's slug follows its name and the suffix does the lookup.
    #   Nullable only while older app versions may still create recipes through v1 without one.
    slug: Mapped[str | None] = mapped_column(Text)
    public_suffix: Mapped[str | None] = mapped_column(Text)

    # Where a copy came from; no live link, and cleared if the source is deleted
    source_recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL", name="fk_recipes_source_recipe_id_recipes"))

    # When the owner published this recipe to the community library (breadsheet#58), or None.
    #   Republishing keeps the original time; unpublishing clears it.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Which step fields the recipe view shows (breadsheet#30): simple or detailed. Switching back to simple
    #   hides the detail fields but never erases them.
    detail_level: Mapped[str] = mapped_column(Text, default="simple", server_default="simple")

    # A draft can be saved incomplete, is visible only to its owner, can't be baked or published, and must
    #   pass validation to go live (breadsheet#30)
    is_draft: Mapped[bool] = mapped_column(default=False, server_default=sql_text("false"))

    # `bread` (the default) or `prep`, such as reviving a starter (breadsheet#59). Validated by the API, not
    #   the database, so adding a category needs no migration.
    category: Mapped[str] = mapped_column(Text, default="bread", server_default="bread")

    # Set when a default is retired: hidden from every recipe list, v1 and v2, but still opens by id or URL
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ## Primary attributes ##
    # Title of the recipe
    name: Mapped[str] = mapped_column(Text)

    # Author & source, all optional
    author: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)

    # Difficulty: Beginner, Intermediate, Advanced, or Expert
    difficulty: Mapped[str] = mapped_column(Text, default="Beginner", server_default="Beginner")

    # Determines how the UI calculates the timing for this recipe
    solve_for_start: Mapped[bool] = mapped_column(default=True, server_default=sql_text("true"))

    ## Datetime attributes ##
    # Stored as UTC; date_added also sets the order of the v1 recipe list
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now,
                                                 server_default=func.now())
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now,
                                                 server_default=func.now())
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now,
                                                    server_default=func.now())

    # Ordered list of steps
    steps: Mapped[list["RecipeStep"]] = relationship(back_populates="recipe",
                                                     order_by="RecipeStep.position",
                                                     cascade="all, delete-orphan",
                                                     passive_deletes=True,
                                                     lazy="selectin")

    # Prep recipes, any one of which gets you ready to start this one, in order (breadsheet#59)
    prerequisite_links: Mapped[list["RecipePrerequisite"]] = relationship(
        foreign_keys="RecipePrerequisite.recipe_id", order_by="RecipePrerequisite.position",
        cascade="all, delete-orphan", passive_deletes=True, lazy="selectin")

    def visible_to(self, viewer) -> bool:
        """Drafts are visible only to their owner; everything else opens for anyone with the id or link."""
        return not self.is_draft or (viewer is not None and self.owner_id == viewer.id)

    def prerequisites_for(self, viewer) -> list["Recipe"]:
        """This recipe's prerequisites in order, leaving out any the viewer can't see (someone else's draft)."""
        return [link.prerequisite for link in self.prerequisite_links if link.prerequisite.visible_to(viewer)]

    @property
    def length(self) -> int:
        """Total duration in seconds: the sum of each step's default wait (its Then Wait). Computed, never stored."""
        return sum(step.default_wait for step in self.steps)

    @property
    def length_max(self) -> int:
        """The longest it could take: each step at the top of its range (or its Then Wait, if that's longer)."""
        return sum(max(step.wait_max, step.default_wait) for step in self.steps)

    def update_from_v1(self, data: dict):
        """
        Applies a v1 request body. Like v1's full-item save, omitted fields reset to their defaults.
        The id and last_modified are managed by the server, so they're ignored.
        """
        now = utc_now()
        self.name = data['name']
        self.author = data.get('author')
        self.source = data.get('source')
        self.url = data.get('url')
        self.difficulty = data.get('difficulty') or "Beginner"
        self.solve_for_start = bool(data.get('solve_for_start', True))
        self.date_added = parse_v1_datetime(data.get('date_added'), fallback=now)
        self.start_time = parse_v1_datetime(data.get('start_time'),
                                            fallback=self.date_added if 'start_time' in data else now)
        self.set_steps_from_v1(data.get('steps'))

    def set_steps_from_v1(self, steps_data: list | None):
        """
        Replaces the step list, in the order provided. Steps whose step_id matches one of this
        recipe's existing steps are updated in place and keep their id; the rest are new.
        """
        existing = {str(step.id): step for step in self.steps}
        new_steps = []

        for position, step_data in enumerate(steps_data or [], start=1):
            step = existing.pop(str(step_data.get('step_id')), None) or RecipeStep()
            step.position = position
            step.text = step_data['text']
            step.note = step_data.get('note')
            step.then_wait = step.wait_min = step.wait_max = int(step_data.get('then_wait') or 0)
            new_steps.append(step)

        self.steps = new_steps

    def to_dict(self, dates_as_epoch=False) -> dict:
        """
        Convert this recipe (including any steps) to a python dictionary.
        Returns dates in ISO format (default), or as a JavaScript-friendly epoch.
        """
        date_added = self.date_added.astimezone(timezone.utc)
        start_time = self.start_time.astimezone(timezone.utc)
        last_modified = self.last_modified.astimezone(timezone.utc)

        output = {
            "id":              str(self.id),
            "name":            self.name,
            "author":          self.author or None,
            "source":          self.source or None,
            "url":             self.url or None,
            "difficulty":      self.difficulty,
            "solve_for_start": self.solve_for_start,
            "length":          self.length,
            "date_added":      date_added.timestamp() * 1000,  # JS timestamps are in ms
            "start_time":      start_time.timestamp() * 1000,
            "last_modified":   last_modified.timestamp() * 1000,
            "steps":           [step.to_dict() for step in self.steps]
        }

        if not dates_as_epoch:
            output['date_added'] = date_added.isoformat()
            output['start_time'] = start_time.isoformat()
            output['last_modified'] = last_modified.isoformat()

        return output

    ## v2 (breadsheet#29) ##
    @property
    def is_default(self) -> bool:
        return self.owner_id is None

    @property
    def path(self) -> str:
        """The user-facing URL path: /recipes/<slug>, or /recipes/<slug>-<suffix> for a personal recipe."""
        return f'/recipes/{self.slug}' if self.is_default else f'/recipes/{self.slug}-{self.public_suffix}'

    def to_v2_summary(self, viewer=None) -> dict:
        """A recipe as it appears in v2 lists: everything but the steps. `viewer` is the signed-in User, if any."""
        return {
            "id":               str(self.id),
            "slug":             self.slug,
            "path":             self.path,
            "scope":            "default" if self.is_default else "personal",
            "owner":            self.owner.username if self.owner else None,
            "is_mine":          viewer is not None and self.owner_id == viewer.id,
            "source_recipe_id": str(self.source_recipe_id) if self.source_recipe_id else None,
            "published_at":     self.published_at.astimezone(timezone.utc).isoformat() if self.published_at else None,
            "detail_level":     self.detail_level,
            "is_draft":         self.is_draft,
            "category":         self.category,
            "prerequisite_ids": [str(recipe.id) for recipe in self.prerequisites_for(viewer)],
            "archived_at":      self.archived_at.astimezone(timezone.utc).isoformat() if self.archived_at else None,
            "name":             self.name,
            "author":           self.author or None,
            "source":           self.source or None,
            "url":              self.url or None,
            "difficulty":       self.difficulty,
            "length_seconds":   self.length,
            "length_max_seconds": self.length_max,
            "step_count":       len(self.steps),
            "created_at":       self.date_added.astimezone(timezone.utc).isoformat(),
            "updated_at":       self.last_modified.astimezone(timezone.utc).isoformat()
        }

    def to_v2_dict(self, viewer=None) -> dict:
        """One recipe in v2, with its steps. Leaves out v1's plan-view state (solve_for_start, start_time)."""
        return {**self.to_v2_summary(viewer),
                "prerequisites": [{"id": str(recipe.id), "name": recipe.name, "path": recipe.path,
                                   "category": recipe.category} for recipe in self.prerequisites_for(viewer)],
                "steps": [step.to_v2_dict() for step in self.steps]}

    def __repr__(self) -> str:
        return f'<Recipe | id: {self.id}, name: {self.name}, length: {self.length}, ' \
               f'steps: {len(self.steps)}>'


class RecipeStep(UuidPrimaryKey, db.Model):
    """Individual step within a Recipe, exposed to v1 clients as a `Step`."""
    __tablename__ = 'recipe_steps'
    __table_args__ = (
        CheckConstraint("wait_min >= 0 AND wait_min <= wait_max", name="wait_range_valid"),
        CheckConstraint("then_wait >= 0", name="then_wait_valid"),
        CheckConstraint("active_seconds >= 0", name="active_seconds_valid"),
    )

    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)

    # Step order, starting at 1; v1's `number`
    position: Mapped[int]

    # Brief summary of the step's directions, plus an optional longer note
    text: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    # The Then Wait: how long to wait after this step before starting the next, in seconds. It's the timing a
    #   bake runs on. Null only for a detailed step that has a range but no Then Wait (breadsheet#30).
    then_wait: Mapped[int | None]

    # The range around the Then Wait. Simple steps have wait_min == wait_max == then_wait. A Then Wait
    #   outside its range is allowed but flagged ("12-24 hours, or skip if your starter is already active").
    wait_min: Mapped[int] = mapped_column(default=0, server_default=sql_text("0"))
    wait_max: Mapped[int] = mapped_column(default=0, server_default=sql_text("0"))

    # Detailed steps only; null means unknown, never zero. Hands-on time counts from the step's start;
    #   needs_presence means you must be home, not just awake.
    active_seconds: Mapped[int | None]
    needs_presence: Mapped[bool | None]

    recipe: Mapped[Recipe] = relationship(back_populates="steps")

    @property
    def default_wait(self) -> int:
        """Where a bake starts this step: its Then Wait, or the middle of its range rounded to the nearest minute."""
        if self.then_wait is not None:
            return self.then_wait
        if self.wait_min == self.wait_max:
            return self.wait_min
        middle = (self.wait_min + self.wait_max) // 2
        rounded = (middle + 30) // 60 * 60
        return min(max(rounded, self.wait_min), self.wait_max)

    def hands_on(self) -> tuple[int, bool, bool]:
        """(hands-on seconds, estimated, needs presence), with the "unknown is not zero" defaults."""
        return hands_on(self.active_seconds, self.needs_presence)

    @property
    def warnings(self) -> list[str]:
        """Allowed but worth a look; the recipe view shows these next to the step."""
        found = []
        if self.then_wait is not None and not self.wait_min <= self.then_wait <= self.wait_max:
            found.append("then_wait_outside_range")
        if self.active_seconds is not None and self.active_seconds > self.default_wait:
            found.append("hands_on_longer_than_wait")
        return found

    def to_v2_dict(self) -> dict:
        return {
            "id":             str(self.id),
            "position":       self.position,
            "text":           self.text,
            "note":           self.note or None,
            "then_wait":      self.then_wait,
            "wait_min":       self.wait_min,
            "wait_max":       self.wait_max,
            "default_wait":   self.default_wait,
            "active_seconds": self.active_seconds,
            "needs_presence": self.needs_presence,
            "warnings":       self.warnings
        }

    def to_dict(self) -> dict:
        return {
            "step_id":   str(self.id),
            "number":    self.position,
            "text":      self.text,
            "then_wait": self.default_wait,
            "note":      self.note or None
        }

    def __repr__(self) -> str:
        return f'<Step #{self.position}, id: {self.id}, then_wait: {self.default_wait}>'


class RecipePrerequisite(db.Model):
    """
    A prep recipe that gets you ready to start another recipe (breadsheet#59). A recipe's prerequisites are
    alternatives: any one satisfies the requirement, listed in `position` order. They're a reminder before a
    bake starts, never enforced. Every prerequisite is a prep recipe and prep recipes have none of their own
    (the API checks both), so there are no chains or cycles. Deleting either recipe removes the link.
    """
    __tablename__ = 'recipe_prerequisites'
    __table_args__ = (
        CheckConstraint("recipe_id <> prerequisite_recipe_id", name="prerequisite_not_self"),
    )

    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"),
                                                         primary_key=True, index=True)
    position: Mapped[int]

    prerequisite: Mapped[Recipe] = relationship(foreign_keys=[prerequisite_recipe_id], lazy="selectin")


class Replacement(UuidPrimaryKey, db.Model):
    """Find-and-replace text used by convert-text to format recipes for Paprika."""
    __tablename__ = 'replacements'
    __table_args__ = (UniqueConstraint("scope", "old"),)

    scope: Mapped[str] = mapped_column(Text)

    # Byte-order collation sorts `old` exactly as DynamoDB sorted its range key. Convert-text applies
    #   replacements in that order, so changing the sort would change its output.
    old: Mapped[str] = mapped_column(Text(collation="C"))
    new: Mapped[str] = mapped_column(Text)

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "old":   self.old,
            "new":   self.new
        }

    def __repr__(self) -> str:
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'


class User(UuidPrimaryKey, db.Model):
    """
    A breadsheet user: a display username plus a secret key. Whoever holds the key is the user.
    Only the key's SHA-256 is stored (see backend/identity.py); the key itself is shown once at signup.
    """
    __tablename__ = 'users'

    # Display handle, kept as typed; unique case-insensitively (see the index below)
    username: Mapped[str] = mapped_column(Text)

    # SHA-256 of the user's key; sign-in looks users up by this
    key_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now,
                                                 server_default=func.now())

    # Refreshed at most daily while the user is active; groundwork for abandoned-username reclamation
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now,
                                                   server_default=func.now())

    # Set only by `flask --app main admins grant` (breadsheet#86); never through the API
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=sql_false())

    def to_dict(self) -> dict:
        return {
            "id":         str(self.id),
            "username":   self.username,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "is_admin":   bool(self.is_admin)
        }

    def __repr__(self) -> str:
        return f'<User | id: {self.id}, username: {self.username}>'


# Usernames are unique regardless of case ("Thomas" and "thomas" can't both exist)
# Unique ignoring case, with `-` and `_` treated as the same (breadsheet#83); see normalized_username()
Index('uq_users_username_normalized', func.replace(func.lower(User.username), '-', '_'), unique=True)


def normalized_username(username: str) -> str:
    """How usernames are compared: lowercase, with `-` as `_`, so bread-head and Bread_Head are the same name."""
    return username.lower().replace('-', '_')


class Bake(UuidPrimaryKey, db.Model):
    """
    A recipe being baked (breadsheet#31): a snapshot of its steps with a schedule anchored to a start or
    finish time. Status is not_started until a step is checked off or skipped, in_progress after, and
    completed once every step is done, the owner completes or cancels it, or an hour passes after its
    projected end. `outcome` records which: finished, canceled, or expired. Expiry is computed on read
    (refresh_status) and written back lazily; no scheduled job.
    """
    __tablename__ = 'bakes'
    __table_args__ = (
        CheckConstraint("anchor_type IN ('start', 'finish')", name="anchor_type_valid"),
        CheckConstraint("alert_mode IN ('simple', 'fancy')", name="alert_mode_valid"),
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name="bake_status_valid"),
        CheckConstraint("created_via IN ('web', 'ha', 'agent')", name="created_via_valid"),
        CheckConstraint("outcome IN ('finished', 'canceled', 'expired')", name="bake_outcome_valid"),
        CheckConstraint("(status = 'completed') = (outcome IS NOT NULL)", name="outcome_only_when_completed"),
        UniqueConstraint("public_suffix", name="uq_bakes_public_suffix"),
        # A repeated start with the same Idempotency-Key returns the original bake
        UniqueConstraint("user_id", "idempotency_key", name="uq_bakes_user_idempotency_key"),
        Index("ix_bakes_user_id_status", "user_id", "status"),
    )

    # /bakes/<public_suffix>; owner only
    public_suffix: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT", name="fk_bakes_user_id_users"))

    # Null once the recipe is deleted; the bake keeps running from its snapshot
    recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL", name="fk_bakes_recipe_id_recipes"), index=True)
    recipe: Mapped[Recipe | None] = relationship(lazy="selectin")
    name_snapshot: Mapped[str] = mapped_column(Text)

    # Step 1 starts at a `start` anchor; with a `finish` anchor, the last step's wait ends at it
    anchor_type: Mapped[str] = mapped_column(Text)
    anchor_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    time_zone: Mapped[str] = mapped_column(Text)  # IANA, e.g. America/Los_Angeles

    alert_mode: Mapped[str] = mapped_column(Text, default="simple", server_default="simple")
    status: Mapped[str] = mapped_column(Text, default="not_started", server_default="not_started")
    created_via: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    projected_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # How a completed bake ended: finished (every step done), canceled by the owner, or expired
    outcome: Mapped[str | None] = mapped_column(Text)

    steps: Mapped[list["BakeStep"]] = relationship(back_populates="bake", order_by="BakeStep.position",
                                                   cascade="all, delete-orphan", passive_deletes=True,
                                                   lazy="selectin")

    @property
    def path(self) -> str:
        return f'/bakes/{self.public_suffix}'

    @property
    def is_active(self) -> bool:
        return self.status != 'completed'

    def project(self):
        """
        Recomputes every scheduled step's time and the projected end. The anchor applies to the first step
        that isn't skipped; each later step's time is the previous step's completion (or its scheduled
        time, if it isn't checked off) plus that step's chosen wait. Skipped steps have no time.
        """
        scheduled = [step for step in self.steps if not step.skipped]
        if self.anchor_type == 'start':
            time = self.anchor_time
        else:
            time = self.anchor_time - timedelta(seconds=sum(step.wait_chosen for step in scheduled))

        for step in self.steps:
            if step.skipped:
                step.scheduled_at = None
                continue
            step.scheduled_at = time
            time = (step.completed_at or step.scheduled_at) + timedelta(seconds=step.wait_chosen)
        self.projected_end = time

    def end(self, outcome: str, at: datetime):
        self.status, self.outcome, self.completed_at = 'completed', outcome, at

    def refresh_status(self, now: datetime) -> bool:
        """
        Moves the status along: in progress once a step is checked off (or the bake started partway
        through); finished once every step is done or skipped; expired an hour after the projected end.
        Skipping a step mid-bake doesn't start a bake on its own. True if it changed.
        """
        if self.status == 'completed':
            return False
        if all(step.is_done for step in self.steps):
            # Finished at the last check-off or mid-bake skip
            moments = [moment for step in self.steps for moment in (step.completed_at, step.skipped_at) if moment]
            self.end('finished', max(moments) if moments else now)
        elif self.projected_end + BAKE_GRACE <= now:
            self.end('expired', self.projected_end + BAKE_GRACE)
        elif self.status == 'not_started' and any(step.completed_at or (step.skipped and not step.skipped_at)
                                                  for step in self.steps):
            self.status = 'in_progress'
        else:
            return False
        return True

    def to_v2_dict(self) -> dict:
        recipe = self.recipe
        zone = self.time_zone
        return {
            "id":             str(self.id),
            "suffix":         self.public_suffix,
            "path":           self.path,
            "name":           self.name_snapshot,
            "recipe_id":      str(self.recipe_id) if self.recipe_id else None,
            "recipe_path":    recipe.path if recipe is not None and not recipe.is_draft else None,
            "recipe_deleted": self.recipe_id is None,
            "anchor_type":    self.anchor_type,
            "anchor_time":    iso(self.anchor_time),
            "time_zone":      zone,
            "alert_mode":     self.alert_mode,
            "status":         self.status,
            "outcome":        self.outcome,
            "created_via":    self.created_via,
            "started_at":     iso(self.started_at),
            "completed_at":   iso(self.completed_at),
            "projected_end":  iso(self.projected_end),
            "projected_end_local": iso(self.projected_end, zone),
            "steps":          [step.to_v2_dict(zone) for step in self.steps]
        }

    def __repr__(self) -> str:
        return f'<Bake | id: {self.id}, recipe: {self.name_snapshot}, status: {self.status}>'


class BakeStep(UuidPrimaryKey, db.Model):
    """One step of a bake: a snapshot of the recipe step at start, plus its schedule and check-off."""
    __tablename__ = 'bake_steps'
    __table_args__ = (
        UniqueConstraint("bake_id", "position", name="uq_bake_steps_bake_id_position"),
        CheckConstraint("wait_chosen >= 0", name="wait_chosen_valid"),
    )

    bake_id: Mapped[UUID] = mapped_column(ForeignKey("bakes.id", ondelete="CASCADE"))
    bake: Mapped[Bake] = relationship(back_populates="steps")
    position: Mapped[int]

    text_snapshot: Mapped[str] = mapped_column(Text)
    note_snapshot: Mapped[str | None] = mapped_column(Text)

    # The recipe step's range at start, and the wait this bake uses (its Then Wait unless changed)
    wait_min: Mapped[int]
    wait_max: Mapped[int]
    wait_chosen: Mapped[int]
    active_seconds: Mapped[int | None]
    needs_presence: Mapped[bool | None]

    # Skipped steps get no time or alerts, and count as done. Steps before the one a bake started at are
    #   skipped with no `skipped_at`; a step skipped mid-bake (breadsheet#78) records the client-supplied time.
    skipped: Mapped[bool] = mapped_column(default=False, server_default=sql_text("false"))
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Null for skipped steps
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The client-supplied moment the user marked it done; the first write wins
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_done(self) -> bool:
        return self.skipped or self.completed_at is not None

    def to_v2_dict(self, zone: str) -> dict:
        seconds, estimated, presence = hands_on(self.active_seconds, self.needs_presence)
        return {
            "position":           self.position,
            "text":               self.text_snapshot,
            "note":               self.note_snapshot,
            "wait_min":           self.wait_min,
            "wait_max":           self.wait_max,
            "wait_chosen":        self.wait_chosen,
            "wait_outside_range": not self.wait_min <= self.wait_chosen <= self.wait_max,
            "active_seconds":     self.active_seconds,
            "needs_presence":     self.needs_presence,
            "hands_on":           {"seconds": seconds, "estimated": estimated, "needs_presence": presence},
            "skipped":            self.skipped,
            "skipped_at":         iso(self.skipped_at),
            "skipped_at_local":   iso(self.skipped_at, zone),
            "scheduled_at":       iso(self.scheduled_at),
            "scheduled_at_local": iso(self.scheduled_at, zone),
            "completed_at":       iso(self.completed_at),
            "completed_at_local": iso(self.completed_at, zone)
        }


class Event(UuidPrimaryKey, db.Model):
    """
    A product event for usage metrics (breadsheet#34; spec: Usage metrics). Pseudonymous: a user id, never
    an IP address, user agent, or free text. `recipe_id` and `bake_id` are plain ids, not foreign keys, so
    events outlive deleted recipes and bakes; deleting a user clears `user_id`. `value` is a number some
    types carry, such as how many seconds late a check-off was.
    """
    __tablename__ = 'events'
    __table_args__ = (
        CheckConstraint("client IN ('web', 'ha', 'agent')", name="event_client_valid"),
        Index('ix_events_type_occurred_at', 'type', 'occurred_at'),
    )

    type: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), index=True)
    # Lets an event be recorded alongside a brand-new user (signup) and saved after it
    user: Mapped[User | None] = relationship()
    recipe_id: Mapped[UUID | None] = mapped_column(Uuid)
    bake_id: Mapped[UUID | None] = mapped_column(Uuid)
    value: Mapped[int | None] = mapped_column()
    client: Mapped[str] = mapped_column(Text, default='web', server_default='web')
    # The agent's self-reported name (X-Breadsheet-Agent), when an agent made the call
    agent_name: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f'<Event | {self.type} at {self.occurred_at}>'


class Connection(UuidPrimaryKey, db.Model):
    """
    A paired Home Assistant instance (breadsheet#27): a device token tied to a user, with scopes. Only the
    token's SHA-256 is stored. Tokens don't expire; revoking sets `revoked_at`, which also cuts off every
    agent calling through that HA (M4).
    """
    __tablename__ = 'connections'

    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    user: Mapped[User] = relationship()
    # What the user sees in their connections list, e.g. the HA instance's name
    label: Mapped[str] = mapped_column(Text)
    # Every pairing grants all four (spec: Decisions, Device token scopes)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    # Refreshed at most daily while the token is used
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Where breadsheet sends "poll now" nudges (breadsheet#93). A secret, like a password: never logged or returned
    webhook_url: Mapped[str | None] = mapped_column(Text)

    def to_v2_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "label":        self.label,
            "scopes":       list(self.scopes),
            "created_at":   iso(self.created_at),
            "last_used_at": iso(self.last_used_at)
        }

    def __repr__(self) -> str:
        return f'<Connection | id: {self.id}, user: {self.user_id}, revoked: {self.revoked_at is not None}>'


class PanelToken(UuidPrimaryKey, db.Model):
    """
    A short-lived token for Home Assistant's sidebar panel (breadsheet-hass#5): the panel embeds the bake view,
    where third-party cookies don't work, so the token rides in the page's URL fragment. It acts as the
    connection's user, for bakes only, for 12 hours, and dies with the connection. Only its SHA-256 is stored.
    """
    __tablename__ = 'panel_tokens'

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    connection_id: Mapped[UUID] = mapped_column(ForeignKey('connections.id', ondelete='CASCADE'), index=True)
    connection: Mapped[Connection] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PairingCode(db.Model):
    """
    A short-lived code for pairing Home Assistant (breadsheet#27): 8 Crockford base32 characters, shown as
    XXXX-XXXX. Ten minutes, single use, one live code per user. Only its SHA-256 is stored.
    """
    __tablename__ = 'pairing_codes'

    code_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    user: Mapped[User] = relationship()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
