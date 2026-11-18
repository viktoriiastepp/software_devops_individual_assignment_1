"""The bookings JSON API through the Flask test client, against the SQL Server test database.
Invalid inputs are tested on purpose: in Assignment 1 one unchecked input caused a 500."""
from datetime import datetime, timedelta


def slot(days=2, hour=18):
    start = (datetime.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return start.strftime("%Y-%m-%dT%H:%M")


def book(client, headers, court_id=1, start=None):
    return client.post("/bookings", json={"court_id": court_id, "start_time": start or slot()}, headers=headers)


# --- accounts ---

def test_register_returns_a_token_and_the_normalised_username(client):
    response = client.post("/auth/register", json={"username": " Ana ", "password": "smash2026"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["username"] == "ana"
    assert body["token"]


def test_register_rejects_a_taken_username_and_weak_password(client):
    client.post("/auth/register", json={"username": "ana", "password": "smash2026"})
    assert client.post("/auth/register", json={"username": "ANA", "password": "smash2026"}).status_code == 400
    response = client.post("/auth/register", json={"username": "ben", "password": "short"})
    assert response.status_code == 400
    assert "at least 8" in response.get_json()["error"]


def test_login_works_and_wrong_password_gets_401(client, login):
    login("ana")
    assert client.post("/auth/login", json={"username": "ana", "password": "smash2026"}).status_code == 200
    assert client.post("/auth/login", json={"username": "ana", "password": "wrong2026"}).status_code == 401


def test_malformed_auth_bodies_get_400_not_500(client):
    assert client.post("/auth/login", data="not json", content_type="application/json").status_code == 400
    assert client.post("/auth/login", json=["ana"]).status_code == 400
    assert client.post("/auth/register", json={"username": 5, "password": "smash2026"}).status_code == 400


# --- bookings ---

def test_courts_are_seeded_by_migration(client):
    assert [c["name"] for c in client.get("/courts").get_json()["courts"]][:2] == ["Court 1", "Court 2"]
    assert len(client.get("/courts").get_json()["courts"]) == 6


def test_booking_needs_a_valid_token(client):
    assert book(client, {}).status_code == 401
    assert book(client, {"Authorization": "Bearer forged.token"}).status_code == 401


def test_create_and_list_my_booking(client, login):
    ana = login("ana")
    response = book(client, ana)
    assert response.status_code == 201
    booking = response.get_json()
    assert booking["court_name"] == "Court 1"
    assert booking["status"] == "active"
    assert [b["id"] for b in client.get("/bookings/mine", headers=ana).get_json()["bookings"]] == [booking["id"]]


def test_overlapping_booking_is_rejected(client, login):
    ana, ben = login("ana"), login("ben")
    book(client, ana)
    response = book(client, ben)
    assert response.status_code == 400
    assert response.get_json()["error"] == "This court is already booked at that time."


def test_invalid_booking_inputs_get_400_with_a_message(client, login):
    ana = login("ana")
    cases = [
        {"court_id": "abc", "start_time": slot()},
        {"court_id": 1.5, "start_time": slot()},
        {"court_id": True, "start_time": slot()},
        {"court_id": 99, "start_time": slot()},
        {"court_id": 1, "start_time": "tomorrow evening"},
        {"court_id": 1},
        {"start_time": slot()},
    ]
    for body in cases:
        response = client.post("/bookings", json=body, headers=ana)
        assert response.status_code == 400, body
        assert response.get_json()["error"]


def test_past_and_late_night_bookings_are_rejected(client, login):
    ana = login("ana")
    assert book(client, ana, start=slot(days=-1)).status_code == 400
    assert book(client, ana, start=slot(hour=22)).status_code == 400


def test_cancel_rules(client, login):
    ana, ben = login("ana"), login("ben")
    booking_id = book(client, ana).get_json()["id"]
    assert client.post(f"/bookings/{booking_id}/cancel", headers=ben).status_code == 403
    response = client.post(f"/bookings/{booking_id}/cancel", headers=ana)
    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelled"
    assert client.post(f"/bookings/{booking_id}/cancel", headers=ana).status_code == 409
    assert client.post("/bookings/999999/cancel", headers=ana).status_code == 404


# --- endpoints the matchmaking service calls across the seam ---

def test_get_one_booking_and_several_by_id(client, login):
    ana = login("ana")
    first = book(client, ana, court_id=1).get_json()["id"]
    second = book(client, ana, court_id=2).get_json()["id"]
    assert client.get(f"/bookings/{first}", headers=ana).get_json()["court_id"] == 1
    assert client.get("/bookings/999999", headers=ana).status_code == 404
    found = client.get(f"/bookings?ids={first},{second},999999", headers=ana).get_json()["bookings"]
    assert [b["id"] for b in found] == [first, second]


def test_lookup_by_ids_rejects_bad_lists(client, login):
    ana = login("ana")
    for query in ["", "?ids=", "?ids=1,x", "?ids=" + ",".join(str(i) for i in range(1, 102))]:
        assert client.get("/bookings" + query, headers=ana).status_code == 400, query


# --- plumbing: health, errors, CORS ---

def test_health_reports_ok_with_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["db"] == "ok"
    assert "version" in response.get_json()


def test_unknown_route_and_wrong_method_answer_json(client):
    assert client.get("/nope").get_json()["error"]
    assert client.delete("/courts").status_code == 405


def test_cors_allows_only_the_ui_origin(client):
    allowed = client.get("/courts", headers={"Origin": "http://localhost:8080"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    other = client.get("/courts", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in other.headers
    preflight = client.options("/bookings", headers={"Origin": "http://localhost:8080"})
    assert preflight.status_code == 204


def test_every_request_is_logged_and_carries_a_request_id(client, caplog):
    caplog.set_level("INFO", logger="access")
    response = client.get("/courts", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"
    assert "method=GET path=/courts status=200" in caplog.text
