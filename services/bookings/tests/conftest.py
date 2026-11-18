import os
from functools import partial

import pytest
from werkzeug.security import generate_password_hash

# Tests use their own database (bookings_test, created by db/init.sql), never the app's data.
# CI sets these variables itself; the defaults are the local-only values from docker-compose.yml.
os.environ.setdefault(
    "DATABASE_URL", "mssql://bookings_app:LocalDev_Bookings_Passw0rd@localhost:1433/bookings_test"
)
os.environ.setdefault("TOKEN_SECRET", "test-only-secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

import db  # noqa: E402
import migrate  # noqa: E402
from accounts import service as accounts_service  # noqa: E402
from app import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """The app uses slow, strong hashing on purpose. Tests use a cheap setting so they run in seconds."""
    monkeypatch.setattr(
        accounts_service,
        "generate_password_hash",
        partial(generate_password_hash, method="pbkdf2:sha256:1000"),
    )


@pytest.fixture(scope="session")
def migrated():
    """Bring the test database up to the latest migration once per test run (this also seeds the courts)."""
    migrate.apply_pending()


@pytest.fixture
def clean_db(migrated):
    """Empty the tables each test writes to. Courts are seed data and stay."""
    with db.transaction() as cursor:
        cursor.execute("DELETE FROM bookings")
        cursor.execute("DELETE FROM users")


@pytest.fixture
def client(clean_db):
    return create_app().test_client()


@pytest.fixture
def login(client):
    """Register a user and return the Authorization header that carries their token."""
    def make(username):
        response = client.post("/auth/register", json={"username": username, "password": "smash2026"})
        return {"Authorization": "Bearer " + response.get_json()["token"]}
    return make
