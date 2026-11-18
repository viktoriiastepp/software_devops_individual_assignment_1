"""SQL for the matchmaking domain. Only this file touches the players, games and game_players tables."""
import db


def get_or_create_player(user_id, name):
    """Players are created the first time a user takes part in matchmaking, starting at rating 1000."""
    with db.transaction() as cursor:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM players WHERE user_id = %s) INSERT INTO players (user_id, name) VALUES (%s, %s)",
            (user_id, user_id, name),
        )
        cursor.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
        return cursor.fetchone()


def get_player(user_id):
    """Read-only lookup: None if this user has never opened or joined a game."""
    return db.fetch_one("SELECT * FROM players WHERE user_id = %s", (user_id,))


def create_game(booking_id):
    row = db.fetch_one("INSERT INTO games (booking_id) OUTPUT INSERTED.id VALUES (%s)", (booking_id,))
    return row["id"]


def get_game(game_id):
    return db.fetch_one("SELECT * FROM games WHERE id = %s", (game_id,))


def list_games_by_status(status):
    return db.fetch_all("SELECT * FROM games WHERE status = %s ORDER BY id", (status,))


def players_in_game(game_id):
    return db.fetch_all(
        "SELECT p.id, p.name, p.rating, gp.team FROM game_players gp "
        "JOIN players p ON p.id = gp.player_id WHERE gp.game_id = %s ORDER BY p.id",
        (game_id,),
    )


def add_player_to_game(game_id, player_id):
    db.execute("INSERT INTO game_players (game_id, player_id) VALUES (%s, %s)", (game_id, player_id))


def assign_teams(game_id, team_1_ids, team_2_ids):
    """Save which team each player is on and mark the game as full, all in one transaction."""
    with db.transaction() as cursor:
        for player_id in team_1_ids:
            cursor.execute("UPDATE game_players SET team = 1 WHERE game_id = %s AND player_id = %s", (game_id, player_id))
        for player_id in team_2_ids:
            cursor.execute("UPDATE game_players SET team = 2 WHERE game_id = %s AND player_id = %s", (game_id, player_id))
        cursor.execute("UPDATE games SET status = 'full' WHERE id = %s", (game_id,))


def record_result(game_id, winning_team, updated_ratings):
    """Save the winner and every player's new rating in one transaction: all or nothing."""
    with db.transaction() as cursor:
        cursor.execute("UPDATE games SET status = 'finished', winning_team = %s WHERE id = %s", (winning_team, game_id))
        for player_id, rating in updated_ratings.items():
            cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (rating, player_id))


def leaderboard(limit=20):
    return db.fetch_all("SELECT TOP (%s) name, rating FROM players ORDER BY rating DESC", (limit,))


def game_for_booking(booking_id):
    return db.fetch_one("SELECT * FROM games WHERE booking_id = %s", (booking_id,))


def games_for_player(player_id):
    return db.fetch_all(
        "SELECT g.* FROM games g JOIN game_players gp ON gp.game_id = g.id "
        "WHERE gp.player_id = %s ORDER BY g.id DESC",
        (player_id,),
    )
