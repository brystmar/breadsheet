"""SQLAlchemy models: recipes, recipe_steps, and replacements (M1); users, recipe scopes and detail (M2)."""
from backend.database import db
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, UniqueConstraint, Uuid, func
from sqlalchemy import text as sql_text  # aliased: RecipeStep has a `text` column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid7


# Scheduling assumes this much hands-on time when a step's active_seconds is unknown (spec: unknown is not zero)
UNKNOWN_HANDS_ON_SECONDS = 10 * 60


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
        return {**self.to_v2_summary(viewer), "steps": [step.to_v2_dict() for step in self.steps]}

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
        """
        (hands-on seconds, estimated, needs presence) for scheduling. Unknown is not zero: a null
        active_seconds means 10 minutes, estimated; a null needs_presence means presence is needed.
        """
        estimated = self.active_seconds is None
        seconds = UNKNOWN_HANDS_ON_SECONDS if estimated else self.active_seconds
        return seconds, estimated, self.needs_presence is not False

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

    def to_dict(self) -> dict:
        return {
            "id":         str(self.id),
            "username":   self.username,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat()
        }

    def __repr__(self) -> str:
        return f'<User | id: {self.id}, username: {self.username}>'


# Usernames are unique regardless of case ("Thomas" and "thomas" can't both exist)
Index('uq_users_username_lower', func.lower(User.username), unique=True)
