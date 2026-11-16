import os

import pytest

# Tests use their own database (matchmaking_test, created by db/init.sql), never the app's data.
# CI sets DATABASE_URL itself; this default is the local-only password from docker-compose.yml.
os.environ.setdefault(
    "DATABASE_URL", "mssql://matchmaking_app:LocalDev_Matchmaking_Passw0rd@localhost:1433/matchmaking_test"
)

import db  # noqa: E402
import migrate  # noqa: E402


@pytest.fixture(scope="session")
def migrated():
    """Bring the test database up to the latest migration once per test run."""
    migrate.apply_pending()


@pytest.fixture
def clean_db(migrated):
    """Empty every matchmaking table before each test, children before parents."""
    with db.transaction() as cursor:
        cursor.execute("DELETE FROM game_players")
        cursor.execute("DELETE FROM games")
        cursor.execute("DELETE FROM players")
