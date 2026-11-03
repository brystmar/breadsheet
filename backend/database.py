"""SQLAlchemy setup for Neon Postgres, shared by the app, Alembic migrations, and tests."""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()

# Neon suspends idle computes, which silently drops pooled connections, so check each one before use.
# The pooled URL goes through PgBouncer in transaction mode, where server-side prepared statements
#   can land on a different backend connection; prepare_threshold=None turns them off in psycopg.
ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "connect_args":  {"connect_timeout": 15, "prepare_threshold": None}
}


def sqlalchemy_url(url: str | None) -> str | None:
    """Points a postgresql:// connection string (as Neon provides it) at the psycopg 3 driver."""
    if url and url.startswith(("postgresql://", "postgres://")):
        return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url
