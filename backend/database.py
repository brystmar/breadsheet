"""Connection helper for Neon Postgres. Not yet used by the API, which still runs on DynamoDB."""
from backend.global_logger import logger
from backend.config import Config
import psycopg


def get_connection() -> psycopg.Connection:
    """Opens a new connection using the pooled DATABASE_URL. Callers should close it, e.g. with `with`."""
    if not Config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set.")

    logger.debug("Opening a Postgres connection.")
    return psycopg.connect(Config.DATABASE_URL, connect_timeout=15)
