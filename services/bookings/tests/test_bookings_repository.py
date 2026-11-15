from datetime import datetime

from bookings import repository as repo

START = datetime(2026, 10, 5, 18, 0)
END = datetime(2026, 10, 5, 19, 30)


def test_six_courts_are_created_at_startup(temp_db):
    assert len(repo.list_courts()) == 6


def test_created_booking_can_be_read_back(temp_db):
    booking_id = repo.create_booking(1, 7, START, END)
    booking = repo.get_booking(booking_id)
    assert booking["user_id"] == 7
    assert booking["start_time"] == "2026-10-05T18:00:00"
    assert booking["status"] == "active"


def test_cancelled_booking_is_kept_but_no_longer_active(temp_db):
    booking_id = repo.create_booking(1, 7, START, END)
    repo.cancel_booking(booking_id, late=True)
    booking = repo.get_booking(booking_id)
    assert booking["status"] == "cancelled"
    assert booking["cancelled_late"] == 1
    assert repo.active_bookings_for_court(1) == []


def test_user_only_sees_their_own_bookings(temp_db):
    repo.create_booking(1, 7, START, END)
    repo.create_booking(2, 8, START, END)
    assert [b["user_id"] for b in repo.bookings_for_user(7)] == [7]
