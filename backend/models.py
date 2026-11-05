"""SQLAlchemy models: recipes, recipe_steps, and replacements (M1); users (M2)."""
from backend.database import db
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, UniqueConstraint, Uuid, func
from sqlalchemy import text as sql_text  # aliased: RecipeStep has a `text` column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid7


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
        """Total duration in seconds: the sum of each step's wait. Computed, never stored."""
        return sum(step.wait_min for step in self.steps)

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
            step.wait_min = step.wait_max = int(step_data.get('then_wait') or 0)
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

    def __repr__(self) -> str:
        return f'<Recipe | id: {self.id}, name: {self.name}, length: {self.length}, ' \
               f'steps: {len(self.steps)}>'


class RecipeStep(UuidPrimaryKey, db.Model):
    """Individual step within a Recipe, exposed to v1 clients as a `Step`."""
    __tablename__ = 'recipe_steps'
    __table_args__ = (
        CheckConstraint("wait_min >= 0 AND wait_min <= wait_max", name="wait_range_valid"),
    )

    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)

    # Step order, starting at 1; v1's `number`
    position: Mapped[int]

    # Brief summary of the step's directions, plus an optional longer note
    text: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    # How long to wait after finishing this step, in seconds. Simple steps have wait_min == wait_max,
    #   which is v1's `then_wait`.
    wait_min: Mapped[int] = mapped_column(default=0, server_default=sql_text("0"))
    wait_max: Mapped[int] = mapped_column(default=0, server_default=sql_text("0"))

    recipe: Mapped[Recipe] = relationship(back_populates="steps")

    def to_dict(self) -> dict:
        return {
            "step_id":   str(self.id),
            "number":    self.position,
            "text":      self.text,
            "then_wait": self.wait_min,
            "note":      self.note or None
        }

    def __repr__(self) -> str:
        return f'<Step #{self.position}, id: {self.id}, then_wait: {self.wait_min}>'


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
