"""Registration and login. Both answer with a signed token the UI sends on later requests."""
from flask import Blueprint

from accounts import service
from api import ApiError, json_body, str_field
from auth import issue_token

bp = Blueprint("accounts", __name__, url_prefix="/auth")


def session_response(user_id, username, status):
    return {"token": issue_token(user_id, username), "user": {"id": user_id, "username": username}}, status


@bp.post("/register")
def register():
    data = json_body()
    user_id, errors = service.register(str_field(data, "username"), str_field(data, "password"))
    if errors:
        return {"error": errors[0], "errors": errors}, 400
    return session_response(user_id, service.normalise(data["username"]), 201)


@bp.post("/login")
def login():
    data = json_body()
    user = service.authenticate(str_field(data, "username"), str_field(data, "password"))
    if user is None:
        raise ApiError(401, "Wrong username or password.")
    return session_response(user["id"], user["username"], 200)
