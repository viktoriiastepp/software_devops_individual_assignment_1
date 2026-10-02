"""SQL for the bookings domain. Only this file touches the courts and bookings tables."""
from db import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS courts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL REFERENCES courts(id),
    user_id INTEGER NOT NULL,  -- belongs to the accounts domain, no FOREIGN KEY on purpose
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    cancelled_late INTEGER NOT NULL DEFAULT 0
);
"""

DEFAULT_COURTS = ["Court 1", "Court 2", "Court 3", "Court 4", "Court 5", "Court 6"]


def init_schema():
    """Create the tables if they don't exist yet and add the club's six courts."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    for name in DEFAULT_COURTS:
        conn.execute("INSERT OR IGNORE INTO courts (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def list_courts():
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM courts ORDER BY id").fetchall()
    conn.close()
    return rows


def active_bookings_for_court(court_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM bookings WHERE court_id = ? AND status = 'active' ORDER BY start_time",
        (court_id,),
    ).fetchall()
    conn.close()
    return rows


def create_booking(court_id, user_id, start, end):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO bookings (court_id, user_id, start_time, end_time) VALUES (?, ?, ?, ?)",
        (court_id, user_id, start.isoformat(), end.isoformat()),
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id


def get_booking(booking_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.close()
    return row


def cancel_booking(booking_id, late):
    conn = get_connection()
    conn.execute(
        "UPDATE bookings SET status = 'cancelled', cancelled_late = ? WHERE id = ?",
        (1 if late else 0, booking_id),
    )
    conn.commit()
    conn.close()


def bookings_for_user(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY start_time", (user_id,)
    ).fetchall()
    conn.close()
    return rows
