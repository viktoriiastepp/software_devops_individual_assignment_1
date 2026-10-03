from functools import partial

import pytest
from werkzeug.security import generate_password_hash

from accounts import repository as accounts_repository
from accounts import service as accounts_service
from bookings import repository as bookings_repository
from matchmaking import repository as matchmaking_repository


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """The app uses slow, strong hashing on purpose. Tests use a cheap setting so they run in seconds."""
    monkeypatch.setattr(
        accounts_service,
        "generate_password_hash",
        partial(generate_password_hash, method="pbkdf2:sha256:1000"),
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder, so each test gets an empty database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    accounts_repository.init_schema()
    bookings_repository.init_schema()
    matchmaking_repository.init_schema()
    return tmp_path


@pytest.fixture
def flask_app(temp_db, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def logged_in(flask_app):
    """Return a function that registers a new user and gives back a test client logged in as them."""
    def make(username):
        client = flask_app.test_client()
        client.post("/register", data={"username": username, "password": "smash2026"})
        return client
    return make
