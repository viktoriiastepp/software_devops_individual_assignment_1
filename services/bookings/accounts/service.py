"""Registration and login. Connects the rules, the database and password hashing."""
from werkzeug.security import check_password_hash, generate_password_hash

from accounts import repository, rules


def normalise(username):
    return username.strip().lower()


def register(username, password):
    """Return (user_id, errors). user_id is None when there are errors."""
    username = normalise(username)
    taken = repository.get_user_by_username(username) is not None
    errors = rules.validate_registration(username, password, taken)
    if errors:
        return None, errors
    user_id = repository.create_user(username, generate_password_hash(password))
    return user_id, []


def authenticate(username, password):
    """Return the user if username and password match, otherwise None.

    Wrong username and wrong password give the same result, so the login
    page never reveals which usernames exist.
    """
    user = repository.get_user_by_username(normalise(username))
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user
