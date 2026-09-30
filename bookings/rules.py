"""Business rules for court bookings. No database code here, so everything is easy to test."""
from datetime import timedelta

OPENING_HOUR = 8
CLOSING_HOUR = 23
SLOT_LENGTH = timedelta(minutes=90)
LATE_CANCEL_WINDOW = timedelta(hours=24)


def end_time_for(start):
    """Every booking is one 90-minute slot."""
    return start + SLOT_LENGTH


def overlaps(start_a, end_a, start_b, end_b):
    """Two bookings clash if each one starts before the other one ends."""
    return start_a < end_b and start_b < end_a


def within_opening_hours(start, end):
    """A booking must start at or after 08:00 and finish by 23:00 on the same day."""
    opening = start.replace(hour=OPENING_HOUR, minute=0, second=0, microsecond=0)
    closing = start.replace(hour=CLOSING_HOUR, minute=0, second=0, microsecond=0)
    return opening <= start and end <= closing


def is_late_cancellation(start, cancel_time):
    """Cancelling less than 24 hours before the booking starts counts as late."""
    return start - cancel_time < LATE_CANCEL_WINDOW


def validate_new_booking(start, now, existing_bookings):
    """Return a list of reasons the booking is not allowed. An empty list means it is allowed.

    existing_bookings is a list of (start, end) pairs for active bookings on the same court.
    """
    errors = []
    end = end_time_for(start)
    if start <= now:
        errors.append("Booking must be in the future.")
    if not within_opening_hours(start, end):
        errors.append("Booking must be between 08:00 and 23:00.")
    for other_start, other_end in existing_bookings:
        if overlaps(start, end, other_start, other_end):
            errors.append("This court is already booked at that time.")
            break
    return errors
