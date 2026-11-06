"""Unit tests for configuration. They must not depend on the git-ignored .env, which CI doesn't have."""
from backend import create_app
from backend.config import Config
from backend.database import sqlalchemy_url
from pytest import raises


def test_the_app_refuses_to_start_without_a_secret_key():
    class NoSecretKey(Config):
        SECRET_KEY = None

    with raises(RuntimeError, match="SECRET_KEY"):
        create_app(NoSecretKey)


def test_sqlalchemy_url():
    # Neon provides postgresql:// URLs; SQLAlchemy needs the psycopg 3 driver named explicitly
    assert sqlalchemy_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert sqlalchemy_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert sqlalchemy_url("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert sqlalchemy_url(None) is None
