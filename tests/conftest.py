import pytest

from accounts import repository as accounts_repository
from bookings import repository as bookings_repository
from matchmaking import repository as matchmaking_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder, so each test gets an empty database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    accounts_repository.init_schema()
    bookings_repository.init_schema()
    matchmaking_repository.init_schema()
    return tmp_path
