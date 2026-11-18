"""Connection to this service's own SQL Server database.

DATABASE_URL has the form mssql://user:password@host:1433/database and is the only
place the connection details come from. Azure SQL serverless pauses when idle, and
while it resumes (up to about a minute) new connections fail with error 40613, so
connect() retries with exponential backoff instead of failing the first request.
"""
import logging
import os
import time
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import pymssql

log = logging.getLogger(__name__)

CONNECT_ATTEMPTS = int(os.environ.get("DB_CONNECT_ATTEMPTS", "8"))
QUERY_TIMEOUT_S = int(os.environ.get("DB_QUERY_TIMEOUT_S", "30"))
MAX_BACKOFF_S = 15


def connection_settings():
    """Split DATABASE_URL into the arguments pymssql.connect() expects."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    parts = urlparse(url)
    return {
        "server": parts.hostname,
        "port": str(parts.port or 1433),
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": parts.path.lstrip("/"),
    }


def connect(attempts=None):
    """Open a connection, retrying 1s, 2s, 4s, 8s, 15s... while the database is unreachable."""
    attempts = attempts or CONNECT_ATTEMPTS
    settings = connection_settings()
    delay = 1
    for attempt in range(1, attempts + 1):
        try:
            return pymssql.connect(
                **settings,
                login_timeout=15,
                timeout=QUERY_TIMEOUT_S,
                tds_version="7.4",
                use_datetime2=True,
            )
        except (pymssql.OperationalError, pymssql.InterfaceError) as error:
            if attempt == attempts:
                raise
            log.warning("database not reachable (attempt %d/%d), retrying in %ds: %s", attempt, attempts, delay, error)
            time.sleep(delay)
            delay = min(delay * 2, MAX_BACKOFF_S)


@contextmanager
def transaction(attempts=None):
    """Give a cursor whose rows are dicts. Commits if the block succeeds, rolls back if it fails."""
    conn = connect(attempts)
    try:
        cursor = conn.cursor(as_dict=True)
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql, params=None):
    with transaction() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def fetch_one(sql, params=None):
    with transaction() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def execute(sql, params=None):
    with transaction() as cursor:
        cursor.execute(sql, params)
