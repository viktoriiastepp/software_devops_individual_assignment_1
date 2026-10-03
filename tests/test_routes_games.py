from datetime import datetime, timedelta


def future_slot(days=2, hour=18):
    start = (datetime.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return start.strftime("%Y-%m-%dT%H:%M")


def book(client):
    client.post("/bookings/", data={"court_id": "1", "start_time": future_slot()})


def open_game(client, booking_id=1):
    return client.post("/games/create", data={"booking_id": str(booking_id)}, follow_redirects=True)


def test_full_game_balances_teams_and_updates_ratings(logged_in):
    players = [logged_in(name) for name in ["ana", "ben", "carla", "dani"]]
    host = players[0]
    book(host)
    open_game(host)
    for client in players[1:]:
        client.post("/games/1/join")

    page = host.get("/games/1")
    assert b"Team 1" in page.data
    assert b"Team 2" in page.data

    response = host.post("/games/1/result", data={"winning_team": "1"}, follow_redirects=True)
    assert b"Result saved and ratings updated." in response.data

    leaderboard = host.get("/games/").data
    assert b"1016" in leaderboard
    assert b"984" in leaderboard


def test_cannot_open_a_game_on_someone_elses_booking(logged_in):
    book(logged_in("ana"))
    response = open_game(logged_in("ben"))
    assert b"You can only open a game on your own active booking." in response.data


def test_joining_twice_is_rejected(logged_in):
    ana = logged_in("ana")
    book(ana)
    open_game(ana)
    response = ana.post("/games/1/join", follow_redirects=True)
    assert b"You have already joined this game." in response.data


def test_cancelled_booking_hides_its_open_game(logged_in):
    ana = logged_in("ana")
    book(ana)
    open_game(ana)
    ana.post("/bookings/1/cancel")
    page = logged_in("ben").get("/games/")
    assert b"No open games right now." in page.data


def test_only_players_in_a_full_game_can_record_a_result(logged_in):
    ana = logged_in("ana")
    book(ana)
    open_game(ana)
    response = logged_in("ben").post("/games/1/result", data={"winning_team": "1"}, follow_redirects=True)
    assert b"Only players in a full game can record its result." in response.data


def test_unknown_game_returns_404(logged_in):
    assert logged_in("ana").get("/games/99").status_code == 404
