"""SQL for the matchmaking domain. Only this file touches the players, games and game_players tables."""
from db import get_connection

SCHEMA = """
-- user_id belongs to the accounts domain: stored as a plain INTEGER, no FOREIGN KEY
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 1000
);

-- booking_id belongs to the bookings domain: plain INTEGER, no FOREIGN KEY (ADR-3)
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'open',
    winning_team INTEGER
);

CREATE TABLE IF NOT EXISTS game_players (
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    team INTEGER,
    PRIMARY KEY (game_id, player_id)
);
"""


def init_schema():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_or_create_player(user_id, name):
    """Players are created the first time a user takes part in matchmaking, starting at rating 1000."""
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO players (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    row = conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_game(booking_id):
    conn = get_connection()
    cursor = conn.execute("INSERT INTO games (booking_id) VALUES (?)", (booking_id,))
    conn.commit()
    game_id = cursor.lastrowid
    conn.close()
    return game_id


def get_game(game_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    return row


def list_games_by_status(status):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM games WHERE status = ? ORDER BY id", (status,)).fetchall()
    conn.close()
    return rows


def players_in_game(game_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT p.id, p.name, p.rating, gp.team FROM game_players gp "
        "JOIN players p ON p.id = gp.player_id WHERE gp.game_id = ? ORDER BY p.id",
        (game_id,),
    ).fetchall()
    conn.close()
    return rows


def add_player_to_game(game_id, player_id):
    conn = get_connection()
    conn.execute("INSERT INTO game_players (game_id, player_id) VALUES (?, ?)", (game_id, player_id))
    conn.commit()
    conn.close()


def assign_teams(game_id, team_1_ids, team_2_ids):
    """Save which team each player is on and mark the game as full, all in one transaction."""
    conn = get_connection()
    with conn:  # commits if everything works, rolls back if anything fails
        for player_id in team_1_ids:
            conn.execute("UPDATE game_players SET team = 1 WHERE game_id = ? AND player_id = ?", (game_id, player_id))
        for player_id in team_2_ids:
            conn.execute("UPDATE game_players SET team = 2 WHERE game_id = ? AND player_id = ?", (game_id, player_id))
        conn.execute("UPDATE games SET status = 'full' WHERE id = ?", (game_id,))
    conn.close()


def record_result(game_id, winning_team, updated_ratings):
    """Save the winner and every player's new rating in one transaction: all or nothing."""
    conn = get_connection()
    with conn:
        conn.execute("UPDATE games SET status = 'finished', winning_team = ? WHERE id = ?", (winning_team, game_id))
        for player_id, rating in updated_ratings.items():
            conn.execute("UPDATE players SET rating = ? WHERE id = ?", (rating, player_id))
    conn.close()


def leaderboard(limit=20):
    conn = get_connection()
    rows = conn.execute("SELECT name, rating FROM players ORDER BY rating DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def game_for_booking(booking_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM games WHERE booking_id = ?", (booking_id,)).fetchone()
    conn.close()
    return row


def games_for_player(player_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT g.* FROM games g JOIN game_players gp ON gp.game_id = g.id "
        "WHERE gp.player_id = ? ORDER BY g.id DESC",
        (player_id,),
    ).fetchall()
    conn.close()
    return rows
