"""Versioned migrations: applies migrations/NNN_name.sql files in order, each exactly once.

Applied versions are recorded in the schema_migrations table, so a second start applies
nothing. Each file runs in one transaction, so it is applied completely or not at all.
A file may hold several batches separated by a line containing only GO, because SQL Server
cannot use a column in the same batch that adds it.
Applied files are never edited; a correction is always a new file.
"""
import logging
import os
import re

import db

log = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
FILE_PATTERN = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
BATCH_SEPARATOR = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)

CREATE_TRACKING_TABLE = """
IF OBJECT_ID('schema_migrations') IS NULL
    CREATE TABLE schema_migrations (
        version CHAR(3) NOT NULL PRIMARY KEY,
        name NVARCHAR(200) NOT NULL,
        applied_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    )
"""


def migration_files():
    """Return (version, file name) pairs in version order, e.g. ("001", "001_init.sql")."""
    names = sorted(name for name in os.listdir(MIGRATIONS_DIR) if FILE_PATTERN.match(name))
    return [(FILE_PATTERN.match(name).group(1), name) for name in names]


def split_batches(sql):
    return [batch for batch in BATCH_SEPARATOR.split(sql) if batch.strip()]


def apply_pending():
    """Apply every migration not yet recorded in schema_migrations. Returns the names applied."""
    db.execute(CREATE_TRACKING_TABLE)
    applied = {row["version"] for row in db.fetch_all("SELECT version FROM schema_migrations")}

    newly_applied = []
    for version, name in migration_files():
        if version in applied:
            continue
        with open(os.path.join(MIGRATIONS_DIR, name), encoding="utf-8") as file:
            batches = split_batches(file.read())
        with db.transaction() as cursor:
            for batch in batches:
                cursor.execute(batch)
            cursor.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (version, name))
        log.info("applied migration %s", name)
        newly_applied.append(name)

    if not newly_applied:
        log.info("database schema up to date, %d migrations already applied", len(applied))
    return newly_applied


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    apply_pending()
