from datetime import datetime, timedelta

from bookings import repository as bookings_repository


def future_slot(days=2, hour=18):
    """A start time a few days ahead, in the format the datetime-local input sends."""
    start = (datetime.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return start.strftime("%Y-%m-%dT%H:%M")


def book(client, court_id=1, start=None):
    data = {"court_id": str(court_id), "start_time": start or future_slot()}
    return client.post("/bookings/", data=data, follow_redirects=True)


def test_pages_redirect_to_login_when_logged_out(flask_app):
    client = flask_app.test_client()
    assert client.get("/login").status_code == 200
    for url in ["/", "/bookings/", "/games/"]:
        response = client.get(url)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_register_logout_and_login_again(logged_in):
    client = logged_in("ana")
    assert b"Welcome, ana" in client.get("/").data
    client.post("/logout")
    wrong = client.post("/login", data={"username": "ana", "password": "wrong2026"})
    assert b"Wrong username or password." in wrong.data
    right = client.post("/login", data={"username": "ana", "password": "smash2026"})
    assert right.status_code == 302


def test_weak_password_shows_an_error(flask_app):
    client = flask_app.test_client()
    response = client.post("/register", data={"username": "ana", "password": "abc"})
    assert b"Password must be at least 8 characters." in response.data


def test_book_a_court(logged_in):
    response = book(logged_in("ana"))
    assert b"Court booked." in response.data
    assert len(bookings_repository.bookings_for_user(1)) == 1


def test_double_booking_the_same_slot_is_rejected(logged_in):
    ana, ben = logged_in("ana"), logged_in("ben")
    slot = future_slot()
    book(ana, start=slot)
    response = book(ben, start=slot)
    assert b"This court is already booked at that time." in response.data


def test_invalid_time_shows_an_error(logged_in):
    response = book(logged_in("ana"), start="not-a-date")
    assert b"Please choose a court and a valid date and time." in response.data


def test_cancel_my_booking(logged_in):
    client = logged_in("ana")
    book(client)
    response = client.post("/bookings/1/cancel", follow_redirects=True)
    assert b"Booking cancelled." in response.data


def test_cannot_cancel_someone_elses_booking(logged_in):
    book(logged_in("ana"))
    response = logged_in("ben").post("/bookings/1/cancel", follow_redirects=True)
    assert b"You can only cancel your own active bookings." in response.data
