"""The only place matchmaking reads data from the bookings domain.
If the two domains become separate services, only this file has to change."""
from bookings import repository as bookings_repository


def active_booking(booking_id):
    booking = bookings_repository.get_booking(booking_id)
    if booking is None or booking["status"] != "active":
        return None
    return booking


def active_bookings_for_user(user_id):
    return [b for b in bookings_repository.bookings_for_user(user_id) if b["status"] == "active"]


def court_names():
    return {court["id"]: court["name"] for court in bookings_repository.list_courts()}
