"""Config file for extending pytest functionality to packages w/o native support."""
from backend import create_app
from backend.config import Config
from backend.database import db
from flask_migrate import downgrade, upgrade
from os import environ
from pytest import fixture, skip
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Disposable local Postgres from docker-compose (`docker compose up -d breadsheet-db`); never Neon
TEST_DATABASE_URL = environ.get('TEST_DATABASE_URL',
                                'postgresql+psycopg://breadsheet:breadsheet@localhost:5433/breadsheet_test')


class TestConfig(Config):
    __test__ = False  # not a test class, despite the name
    TESTING = True
    SQLALCHEMY_DATABASE_URI = TEST_DATABASE_URL
    MIGRATIONS_DATABASE_URI = TEST_DATABASE_URL
    SECRET_KEY = 'test-only-secret-key'
    SESSION_COOKIE_SECURE = False  # the test client uses plain http


@fixture(scope='session')
def app():
    """The Flask app, configured for the test database. Creating it doesn't connect to the database."""
    return create_app(TestConfig)


@fixture(scope='session')
def database(app):
    """Rebuilds the test database's schema from the Alembic migrations, so tests also cover them."""
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        skip("Test Postgres isn't running; start it with `docker compose up -d breadsheet-db`.")
    finally:
        engine.dispose()

    with app.app_context():
        downgrade(revision='base')
        upgrade()

    yield db


@fixture(scope='function')
def client(app, database):
    """A test client with empty tables."""
    with app.app_context():
        database.session.execute(text("TRUNCATE recipes, recipe_steps, replacements, users"))
        database.session.commit()

    # Rate-limit counters live in the in-process cache locally; start each test from zero
    from backend.cache import cache
    cache.clear()

    with app.test_client() as test_client:
        yield test_client
