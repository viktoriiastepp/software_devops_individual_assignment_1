"""Games, players and the leaderboard. GET routes only read; players are created only on POST.

Booking details come from the bookings service through bookings_client (the seam). When it is
unavailable, reads degrade (cached details plus a notice) and writes that need it answer 503.
"""
from flask import Blueprint, g

from api import ApiError, int_field, json_body
from auth import require_user
from matchmaking import bookings_client, repository, rules

bp = Blueprint("matchmaking", __name__)

BOOKINGS_DOWN = "Court details are temporarily unavailable. Please try again in a minute."
DEFAULT_RATING = 1000


def current_player():
    """Used by POST routes only: creates the player the first time they open or join a game."""
    return repository.get_or_create_player(g.user_id, g.username)


def game_json(game, booking, players):
    return {
        "id": game["id"],
        "booking_id": game["booking_id"],
        "status": game["status"],
        "winning_team": game["winning_team"],
        "booking": booking,  # None when the bookings service is unavailable and nothing is cached
        "level": round(sum(p["rating"] for p in players) / len(players)) if players else None,
        "players": [{"id": p["id"], "name": p["name"], "rating": p["rating"], "team": p["team"]} for p in players],
    }


def load_game(game_id):
    game = repository.get_game(game_id)
    if game is None:
        raise ApiError(404, "Game not found.")
    return game


@bp.get("/games/open")
@require_user
def open_games():
    games = repository.list_games_by_status("open")
    bookings, stale = bookings_client.get_bookings([game["booking_id"] for game in games])
    result = []
    for game in games:
        booking = bookings.get(game["booking_id"])
        if booking is not None and booking["status"] != "active":
            continue  # the court booking was cancelled, so the game is hidden
        result.append(game_json(game, booking, repository.players_in_game(game["id"])))
    return {"games": result, "notice": BOOKINGS_DOWN if stale else None}


@bp.get("/games/mine")
@require_user
def my_games():
    player = repository.get_player(g.user_id)
    games = repository.games_for_player(player["id"]) if player else []
    bookings, stale = bookings_client.get_bookings([game["booking_id"] for game in games])
    return {
        "games": [game_json(game, bookings.get(game["booking_id"]), repository.players_in_game(game["id"])) for game in games],
        "notice": BOOKINGS_DOWN if stale else None,
    }


def full_game(game_id):
    """A game with its players and its booking details (cached, with a notice, if bookings is down)."""
    game = load_game(game_id)
    bookings, stale = bookings_client.get_bookings([game["booking_id"]])
    result = game_json(game, bookings.get(game["booking_id"]), repository.players_in_game(game_id))
    result["notice"] = BOOKINGS_DOWN if stale else None
    return result


@bp.get("/games/<int:game_id>")
@require_user
def game_detail(game_id):
    return full_game(game_id)


@bp.post("/games")
@require_user
def create_game():
    booking_id = int_field(json_body(), "booking_id")
    try:
        booking = bookings_client.get_booking(booking_id)  # cross-seam call: needs fresh data
    except bookings_client.BookingsUnavailable:
        raise ApiError(503, BOOKINGS_DOWN) from None
    if booking is None or booking["user_id"] != g.user_id:
        raise ApiError(403, "You can only open a game on your own booking.")
    if booking["status"] != "active":
        raise ApiError(409, "This booking was cancelled.")
    if repository.game_for_booking(booking_id) is not None:
        raise ApiError(409, "This booking already has a game.")
    game_id = repository.create_game(booking_id)
    repository.add_player_to_game(game_id, current_player()["id"])
    return game_json(repository.get_game(game_id), booking, repository.players_in_game(game_id)), 201


@bp.post("/games/<int:game_id>/join")
@require_user
def join_game(game_id):
    game = load_game(game_id)
    if game["status"] != "open":
        raise ApiError(409, "This game is not open for joining.")
    player = current_player()
    players = repository.players_in_game(game_id)
    errors = rules.validate_join(
        player["rating"], [p["rating"] for p in players], already_joined=any(p["id"] == player["id"] for p in players)
    )
    if errors:
        return {"error": errors[0], "errors": errors}, 400

    repository.add_player_to_game(game_id, player["id"])
    players = repository.players_in_game(game_id)
    if len(players) == rules.PLAYERS_PER_GAME:
        team_1, team_2 = rules.balanced_teams([(p["id"], p["rating"]) for p in players])
        repository.assign_teams(game_id, [pid for pid, _ in team_1], [pid for pid, _ in team_2])
    return full_game(game_id)


@bp.post("/games/<int:game_id>/result")
@require_user
def record_result(game_id):
    winning_team = int_field(json_body(), "winning_team")
    if winning_team not in (1, 2):
        raise ApiError(400, "'winning_team' must be 1 or 2.")
    game = load_game(game_id)
    players = repository.players_in_game(game_id)
    player = repository.get_player(g.user_id)
    if game["status"] != "full" or player is None or not any(p["id"] == player["id"] for p in players):
        raise ApiError(409, "Only players in a full game can record its result, once.")

    team_1 = [(p["id"], p["rating"]) for p in players if p["team"] == 1]
    team_2 = [(p["id"], p["rating"]) for p in players if p["team"] == 2]
    repository.record_result(game_id, winning_team, rules.new_ratings(team_1, team_2, team_1_won=(winning_team == 1)))
    return full_game(game_id)


@bp.get("/players/me")
@require_user
def me():
    player = repository.get_player(g.user_id)  # read-only: a new member simply has the starting rating
    return {"name": g.username, "rating": player["rating"] if player else DEFAULT_RATING}


@bp.get("/leaderboard")
def leaderboard():
    return {"players": [{"name": p["name"], "rating": p["rating"]} for p in repository.leaderboard()]}
