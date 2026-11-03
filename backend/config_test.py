"""Unit tests for the Config class to ensure the environment variables are loaded."""
from backend.config import Config
from backend.database import sqlalchemy_url


def test_config():
    # App-related
    assert Config.SECRET_KEY is not None
    assert Config.DOMAIN_URL is not None


def test_sqlalchemy_url():
    # Neon provides postgresql:// URLs; SQLAlchemy needs the psycopg 3 driver named explicitly
    assert sqlalchemy_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert sqlalchemy_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert sqlalchemy_url("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert sqlalchemy_url(None) is None
