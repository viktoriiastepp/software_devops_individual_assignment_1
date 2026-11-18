"""The matchmaking JSON API against the SQL Server test database, with the bookings service stubbed."""
from conftest import auth

ANA, BEN, CARLA, DANI = auth(1, "ana"), auth(2, "ben"), auth(3, "carla"), auth(4, "dani")


def open_game(client, bookings, headers=ANA, booking_id=10, owner=1):
    bookings.add(booking_id, owner)
    return client.post("/games", json={"booking_id": booking_id}, headers=headers)


def test_requests_without_a_valid_token_get_401(client, bookings):
    assert client.get("/games/open").status_code == 401
    assert client.get("/games/open", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_open_a_game_on_my_active_booking(client, bookings):
    response = open_game(client, bookings)
    assert response.status_code == 201
    game = response.get_json()
    assert game["status"] == "open"
    assert game["booking"]["court_name"] == "Court 1"
    assert [p["name"] for p in game["players"]] == ["ana"]


def test_cannot_open_a_game_on_someone_elses_missing_or_cancelled_booking(client, bookings):
    bookings.add(20, user_id=2)
    assert client.post("/games", json={"booking_id": 20}, headers=ANA).status_code == 403
    assert client.post("/games", json={"booking_id": 404}, headers=ANA).status_code == 403
    bookings.add(21, user_id=1, status="cancelled")
    assert client.post("/games", json={"booking_id": 21}, headers=ANA).status_code == 409


def test_second_game_on_the_same_booking_is_rejected(client, bookings):
    open_game(client, bookings)
    assert client.post("/games", json={"booking_id": 10}, headers=ANA).status_code == 409


def test_invalid_inputs_get_400_not_500(client, bookings):
    """Assignment 1 feedback: a non-numeric booking_id caused a 500."""
    for body in [{"booking_id": "abc"}, {"booking_id": 1.5}, {"booking_id": None}, {}]:
        assert client.post("/games", json=body, headers=ANA).status_code == 400, body
    assert client.post("/games", data="not json", content_type="application/json", headers=ANA).status_code == 400
    game_id = open_game(client, bookings).get_json()["id"]
    for body in [{"winning_team": 3}, {"winning_team": "first"}, {}]:
        assert client.post(f"/games/{game_id}/result", json=body, headers=ANA).status_code == 400, body


def test_fourth_join_balances_teams_and_result_updates_ratings(client, bookings):
    game_id = open_game(client, bookings).get_json()["id"]
    for headers in (BEN, CARLA):
        assert client.post(f"/games/{game_id}/join", headers=headers).get_json()["status"] == "open"
    full = client.post(f"/games/{game_id}/join", headers=DANI).get_json()
    assert full["status"] == "full"
    assert sorted(p["team"] for p in full["players"]) == [1, 1, 2, 2]

    finished = client.post(f"/games/{game_id}/result", json={"winning_team": 1}, headers=ANA).get_json()
    assert finished["status"] == "finished"
    assert sorted(p["rating"] for p in finished["players"]) == [984, 984, 1016, 1016]
    assert client.post(f"/games/{game_id}/result", json={"winning_team": 1}, headers=ANA).status_code == 409


def test_join_rules(client, bookings):
    game_id = open_game(client, bookings).get_json()["id"]
    assert client.post(f"/games/{game_id}/join", headers=ANA).status_code == 400  # already in
    assert client.post("/games/999999/join", headers=BEN).status_code == 404


def test_only_players_of_a_full_game_record_the_result(client, bookings):
    game_id = open_game(client, bookings).get_json()["id"]
    assert client.post(f"/games/{game_id}/result", json={"winning_team": 1}, headers=ANA).status_code == 409
    for headers in (BEN, CARLA, DANI):
        client.post(f"/games/{game_id}/join", headers=headers)
    outsider = auth(5, "eva")
    assert client.post(f"/games/{game_id}/result", json={"winning_team": 1}, headers=outsider).status_code == 409


def test_get_requests_never_create_players(client, bookings):
    """Assignment 1 feedback: opening a page inserted a player row. Now only POST routes write."""
    assert client.get("/players/me", headers=ANA).get_json() == {"name": "ana", "rating": 1000}
    assert client.get("/games/mine", headers=ANA).get_json()["games"] == []
    assert client.get("/leaderboard").get_json()["players"] == []


def test_open_games_hide_cancelled_bookings(client, bookings):
    open_game(client, bookings, booking_id=10)
    open_game(client, bookings, headers=BEN, booking_id=11, owner=2)
    bookings.bookings[11]["status"] = "cancelled"
    assert [g["booking_id"] for g in client.get("/games/open", headers=ANA).get_json()["games"]] == [10]


def test_when_bookings_is_down_reads_degrade_and_creating_a_game_gets_503(client, bookings):
    game_id = open_game(client, bookings).get_json()["id"]
    bookings.up = False
    listing = client.get("/games/open", headers=ANA)
    assert listing.status_code == 200
    assert listing.get_json()["notice"].startswith("Court details are temporarily unavailable")
    assert client.get(f"/games/{game_id}", headers=ANA).get_json()["players"][0]["name"] == "ana"
    bookings.add(12, user_id=1)
    response = client.post("/games", json={"booking_id": 12}, headers=ANA)
    assert response.status_code == 503
    assert response.get_json()["error"].startswith("Court details are temporarily unavailable")


def test_health_and_leaderboard(client, bookings):
    assert client.get("/health").get_json()["db"] == "ok"
    game_id = open_game(client, bookings).get_json()["id"]
    for headers in (BEN, CARLA, DANI):
        client.post(f"/games/{game_id}/join", headers=headers)
    client.post(f"/games/{game_id}/result", json={"winning_team": 2}, headers=ANA)
    assert client.get("/leaderboard").get_json()["players"][0]["rating"] == 1016
