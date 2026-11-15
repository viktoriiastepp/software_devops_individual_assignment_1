from functools import partial

import pytest
from werkzeug.security import generate_password_hash

from accounts import repository as accounts_repository
from accounts import service as accounts_service
from bookings import repository as bookings_repository


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
    return tmp_path
