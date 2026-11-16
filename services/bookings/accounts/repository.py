"""SQL for the accounts domain. Only this file touches the users table."""
import db


def create_user(username, password_hash):
    row = db.fetch_one(
        "INSERT INTO users (username, password_hash) OUTPUT INSERTED.id VALUES (%s, %s)",
        (username, password_hash),
    )
    return row["id"]


def get_user(user_id):
    return db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))


def get_user_by_username(username):
    return db.fetch_one("SELECT * FROM users WHERE username = %s", (username,))
