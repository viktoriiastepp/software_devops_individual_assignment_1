from datetime import datetime

from bookings import rules


def dt(day, hour, minute=0):
    """Helper: a datetime in October 2026."""
    return datetime(2026, 10, day, hour, minute)


def test_overlapping_bookings_clash():
    assert rules.overlaps(dt(2, 18), dt(2, 19, 30), dt(2, 19), dt(2, 20, 30))


def test_back_to_back_bookings_do_not_clash():
    assert not rules.overlaps(dt(2, 18), dt(2, 19, 30), dt(2, 19, 30), dt(2, 21))


def test_booking_inside_opening_hours_is_allowed():
    assert rules.within_opening_hours(dt(2, 8), dt(2, 9, 30))


def test_booking_before_opening_is_rejected():
    assert not rules.within_opening_hours(dt(2, 7, 30), dt(2, 9))


def test_booking_ending_after_closing_is_rejected():
    assert not rules.within_opening_hours(dt(2, 22), dt(2, 23, 30))


def test_cancellation_less_than_24_hours_before_is_late():
    assert rules.is_late_cancellation(dt(2, 18), dt(2, 9))


def test_cancellation_exactly_24_hours_before_is_not_late():
    assert not rules.is_late_cancellation(dt(3, 18), dt(2, 18))


def test_valid_booking_has_no_errors():
    assert rules.validate_new_booking(dt(3, 18), now=dt(2, 9), existing_bookings=[]) == []


def test_booking_in_the_past_is_rejected():
    errors = rules.validate_new_booking(dt(1, 18), now=dt(2, 9), existing_bookings=[])
    assert "Booking must be in the future." in errors


def test_booking_on_a_taken_slot_is_rejected():
    taken = [(dt(3, 18), dt(3, 19, 30))]
    errors = rules.validate_new_booking(dt(3, 19), now=dt(2, 9), existing_bookings=taken)
    assert "This court is already booked at that time." in errors


def test_booking_outside_opening_hours_is_rejected():
    errors = rules.validate_new_booking(dt(3, 22), now=dt(2, 9), existing_bookings=[])
    assert "Booking must be between 08:00 and 23:00." in errors
