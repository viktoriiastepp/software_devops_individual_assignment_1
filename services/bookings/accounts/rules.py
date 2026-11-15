"""Rules for creating an account. No database code here."""
import re

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 8


def validate_registration(username, password, username_taken):
    """Return a list of problems with the new account. An empty list means it is valid."""
    errors = []
    if not USERNAME_PATTERN.match(username):
        errors.append("Username must be 3-20 characters: letters, numbers or underscores.")
    if username_taken:
        errors.append("That username is already taken.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append("Password must be at least 8 characters.")
    elif not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        errors.append("Password must contain both letters and numbers.")
    return errors
