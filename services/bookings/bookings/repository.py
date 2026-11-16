"""SQL for the bookings domain. Only this file touches the courts and bookings tables."""
import db

DEFAULT_COURTS = ["Court 1", "Court 2", "Court 3", "Court 4", "Court 5", "Court 6"]


def seed_courts():
    """Add the club's six courts if they are missing. Safe to run on every start."""
    for name in DEFAULT_COURTS:
        db.execute(
            "IF NOT EXISTS (SELECT 1 FROM courts WHERE name = %s) INSERT INTO courts (name) VALUES (%s)",
            (name, name),
        )


def list_courts():
    return db.fetch_all("SELECT id, name FROM courts ORDER BY id")


def active_bookings_for_court(court_id):
    return db.fetch_all(
        "SELECT * FROM bookings WHERE court_id = %s AND status = 'active' ORDER BY start_time",
        (court_id,),
    )


def create_booking(court_id, user_id, start, end):
    row = db.fetch_one(
        "INSERT INTO bookings (court_id, user_id, start_time, end_time) OUTPUT INSERTED.id VALUES (%s, %s, %s, %s)",
        (court_id, user_id, start, end),
    )
    return row["id"]


def get_booking(booking_id):
    return db.fetch_one("SELECT * FROM bookings WHERE id = %s", (booking_id,))


def cancel_booking(booking_id, late):
    db.execute(
        "UPDATE bookings SET status = 'cancelled', cancelled_late = %s WHERE id = %s",
        (1 if late else 0, booking_id),
    )


def bookings_for_user(user_id):
    return db.fetch_all("SELECT * FROM bookings WHERE user_id = %s ORDER BY start_time", (user_id,))
