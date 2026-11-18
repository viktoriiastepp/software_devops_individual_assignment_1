"""SQL for the bookings domain. Only this file touches the courts and bookings tables."""
import db

# every booking is read together with its court name, which lives in the same database
BOOKING_COLUMNS = """
    SELECT b.id, b.court_id, c.name AS court_name, b.user_id, b.start_time, b.end_time, b.status, b.cancelled_late
    FROM bookings b JOIN courts c ON c.id = b.court_id
"""


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
    return db.fetch_one(BOOKING_COLUMNS + " WHERE b.id = %s", (booking_id,))


def get_bookings(booking_ids):
    """Bookings for a list of ids; ids that do not exist are simply missing from the result."""
    placeholders = ", ".join(["%s"] * len(booking_ids))
    return db.fetch_all(BOOKING_COLUMNS + f" WHERE b.id IN ({placeholders}) ORDER BY b.id", tuple(booking_ids))


def cancel_booking(booking_id, late):
    db.execute(
        "UPDATE bookings SET status = 'cancelled', cancelled_late = %s WHERE id = %s",
        (1 if late else 0, booking_id),
    )


def bookings_for_user(user_id):
    return db.fetch_all(BOOKING_COLUMNS + " WHERE b.user_id = %s ORDER BY b.start_time", (user_id,))
