from backend.config import Config
from pytest import mark


@mark.skipif(not Config.DATABASE_URL, reason="DATABASE_URL not set")
class TestDatabase:
    def test_round_trip(self):
        """Creates a temp table, writes a row, and reads it back from Neon Postgres."""
        from backend.database import get_connection
        from psycopg import sql
        from uuid import uuid4

        # The pooled connection reuses server sessions, so use a unique name and drop the table at commit
        table = sql.Identifier(f"ping_{uuid4().hex}")

        with get_connection() as conn:
            conn.execute(sql.SQL("CREATE TEMP TABLE {} (id serial PRIMARY KEY, note text) ON COMMIT DROP").format(table))
            conn.execute(sql.SQL("INSERT INTO {} (note) VALUES (%s)").format(table), ("hello neon",))
            row = conn.execute(sql.SQL("SELECT note FROM {}").format(table)).fetchone()
            version = conn.execute("SHOW server_version").fetchone()[0]

        assert row[0] == "hello neon"
        assert version.startswith("18")
