from backend.config import Config
from pytest import mark


@mark.skipif(not Config.DATABASE_URL, reason="DATABASE_URL not set")
class TestDatabase:
    def test_round_trip(self):
        """Connects to Neon through the pooled URL with the app's engine settings, and generates a UUIDv7."""
        from backend.database import ENGINE_OPTIONS, sqlalchemy_url
        from sqlalchemy import create_engine, text

        engine = create_engine(sqlalchemy_url(Config.DATABASE_URL), **ENGINE_OPTIONS)
        try:
            with engine.connect() as conn:
                version = conn.execute(text("SHOW server_version")).scalar()
                new_id = conn.execute(text("SELECT uuidv7()")).scalar()
        finally:
            engine.dispose()

        assert version.startswith("18")
        assert new_id.version == 7
