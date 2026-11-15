from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from accounts.routes import login_required
from matchmaking import booking_lookup, repository, rules

bp = Blueprint("matchmaking", __name__, url_prefix="/games")


def current_player():
    return repository.get_or_create_player(session["user_id"], session["username"])


@bp.route("/")
@login_required
def index():
    player = current_player()
    court_names = booking_lookup.court_names()

    open_games = []
    for game in repository.list_games_by_status("open"):
        booking = booking_lookup.active_booking(game["booking_id"])
        if booking is None:  # booking was cancelled, so the game is hidden
            continue
        players = repository.players_in_game(game["id"])
        level = round(sum(p["rating"] for p in players) / len(players))
        open_games.append({"game": game, "booking": booking, "players": players, "level": level})

    bookable = [
        b for b in booking_lookup.active_bookings_for_user(session["user_id"])
        if repository.game_for_booking(b["id"]) is None
    ]
    return render_template(
        "games.html",
        player=player,
        court_names=court_names,
        open_games=open_games,
        bookable=bookable,
        my_games=repository.games_for_player(player["id"]),
        leaderboard=repository.leaderboard(),
    )


@bp.route("/create", methods=["POST"])
@login_required
def create():
    booking_id = int(request.form["booking_id"])
    booking = booking_lookup.active_booking(booking_id)
    if booking is None or booking["user_id"] != session["user_id"]:
        flash("You can only open a game on your own active booking.")
    elif repository.game_for_booking(booking_id) is not None:
        flash("This booking already has a game.")
    else:
        game_id = repository.create_game(booking_id)
        repository.add_player_to_game(game_id, current_player()["id"])
        flash("Game opened. Players at your level can now join.", "success")
    return redirect(url_for("matchmaking.index"))


@bp.route("/<int:game_id>/join", methods=["POST"])
@login_required
def join(game_id):
    game = repository.get_game(game_id)
    if game is None or game["status"] != "open":
        flash("This game is not open for joining.")
        return redirect(url_for("matchmaking.index"))

    player = current_player()
    players = repository.players_in_game(game_id)
    errors = rules.validate_join(
        player["rating"],
        [p["rating"] for p in players],
        already_joined=any(p["id"] == player["id"] for p in players),
    )
    if errors:
        for error in errors:
            flash(error)
        return redirect(url_for("matchmaking.index"))

    repository.add_player_to_game(game_id, player["id"])
    players = repository.players_in_game(game_id)
    if len(players) == rules.PLAYERS_PER_GAME:
        team_1, team_2 = rules.balanced_teams([(p["id"], p["rating"]) for p in players])
        repository.assign_teams(game_id, [pid for pid, _ in team_1], [pid for pid, _ in team_2])
        flash("The game is full and the teams have been balanced.", "success")
    else:
        flash("You joined the game.", "success")
    return redirect(url_for("matchmaking.detail", game_id=game_id))


@bp.route("/<int:game_id>")
@login_required
def detail(game_id):
    game = repository.get_game(game_id)
    if game is None:
        abort(404)
    players = repository.players_in_game(game_id)
    booking = booking_lookup.active_booking(game["booking_id"])
    court_name = booking_lookup.court_names().get(booking["court_id"]) if booking else None
    player_id = current_player()["id"]
    return render_template(
        "game.html",
        game=game,
        players=players,
        booking=booking,
        court_name=court_name,
        is_player=any(p["id"] == player_id for p in players),
    )


@bp.route("/<int:game_id>/result", methods=["POST"])
@login_required
def result(game_id):
    game = repository.get_game(game_id)
    players = repository.players_in_game(game_id) if game else []
    player_id = current_player()["id"]
    if game is None or game["status"] != "full" or not any(p["id"] == player_id for p in players):
        flash("Only players in a full game can record its result.")
        return redirect(url_for("matchmaking.index"))

    winning_team = request.form.get("winning_team")
    if winning_team not in ("1", "2"):
        flash("Choose which team won.")
        return redirect(url_for("matchmaking.detail", game_id=game_id))
    winning_team = int(winning_team)

    team_1 = [(p["id"], p["rating"]) for p in players if p["team"] == 1]
    team_2 = [(p["id"], p["rating"]) for p in players if p["team"] == 2]
    updated = rules.new_ratings(team_1, team_2, team_1_won=(winning_team == 1))
    repository.record_result(game_id, winning_team, updated)
    flash("Result saved and ratings updated.", "success")
    return redirect(url_for("matchmaking.detail", game_id=game_id))
