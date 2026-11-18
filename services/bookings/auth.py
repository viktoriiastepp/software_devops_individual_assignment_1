"""Signed login tokens. The bookings service issues them; both services verify them.

A token is the user's id and username signed with TOKEN_SECRET (itsdangerous, part of Flask).
Nobody can change the content without the secret, and it expires after TOKEN_MAX_AGE_S.
Each service has its own copy of this file, so neither imports code from the other.
"""
import os
from functools import wraps

from flask import g, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api import ApiError

TOKEN_MAX_AGE_S = int(os.environ.get("TOKEN_MAX_AGE_S", str(7 * 24 * 3600)))


def _serializer():
    secret = os.environ.get("TOKEN_SECRET")
    if not secret:
        raise RuntimeError("TOKEN_SECRET is not set")
    return URLSafeTimedSerializer(secret, salt="padel-login")


def issue_token(user_id, username):
    return _serializer().dumps({"user_id": user_id, "username": username})


def require_user(view):
    """Decorator: the route runs only with a valid token; g.user_id and g.username are then set."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ApiError(401, "Please log in.")
        try:
            data = _serializer().loads(header.removeprefix("Bearer "), max_age=TOKEN_MAX_AGE_S)
        except BadSignature:  # also covers expired tokens
            raise ApiError(401, "Your login is invalid or has expired. Please log in again.") from None
        g.user_id = data["user_id"]
        g.username = data["username"]
        return view(*args, **kwargs)
    return wrapped
