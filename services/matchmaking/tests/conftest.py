import os

import pytest

# Tests use their own database (matchmaking_test, created by db/init.sql), never the app's data.
# CI sets these variables itself; the defaults are the local-only values from docker-compose.yml.
os.environ.setdefault(
    "DATABASE_URL", "mssql://matchmaking_app:LocalDev_Matchmaking_Passw0rd@localhost:1433/matchmaking_test"
)
os.environ.setdefault("TOKEN_SECRET", "test-only-secret")

import db  # noqa: E402
import migrate  # noqa: E402
from app import create_app  # noqa: E402
from auth import issue_token  # noqa: E402
from matchmaking import bookings_client  # noqa: E402


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


@pytest.fixture
def client(clean_db):
    return create_app().test_client()


def auth(user_id, username):
    """The header the UI sends: a token signed with the same secret the bookings service uses."""
    return {"Authorization": "Bearer " + issue_token(user_id, username)}


class FakeBookings:
    """Stands in for the bookings service in unit tests (the real HTTP call is tested in
    test_bookings_client.py and across both services in the integration test)."""

    def __init__(self):
        self.bookings = {}
        self.up = True

    def add(self, booking_id, user_id, status="active"):
        self.bookings[booking_id] = {
            "id": booking_id, "court_id": 1, "court_name": "Court 1", "user_id": user_id,
            "start_time": "2026-12-01T18:00", "end_time": "2026-12-01T19:30", "status": status, "cancelled_late": False,
        }

    def get_booking(self, booking_id):
        if not self.up:
            raise bookings_client.BookingsUnavailable("down")
        return self.bookings.get(booking_id)

    def get_bookings(self, booking_ids):
        if not self.up:
            return {}, True
        return {i: self.bookings[i] for i in booking_ids if i in self.bookings}, False


@pytest.fixture
def bookings(monkeypatch):
    fake = FakeBookings()
    monkeypatch.setattr(bookings_client, "get_booking", fake.get_booking)
    monkeypatch.setattr(bookings_client, "get_bookings", fake.get_bookings)
    return fake
