"""JSON API plumbing shared by every route: CORS, JSON errors and input validation.

Every error leaves the service as JSON with a clear message and the right status code,
never as an HTML page or a stack trace (Assignment 1 feedback: one bad input gave a 500).
"""
import logging
import os
from datetime import datetime

from flask import request
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)

# Comma-separated list of browser origins allowed to call this service, e.g. the Static Web App URL.
ALLOWED_ORIGINS = {o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()}


class ApiError(Exception):
    """Raised by a route to stop and answer with a status code and a message."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def json_body():
    """The request body as a dict, or a 400 if it is missing or not a JSON object."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object.")
    return data


def int_field(data, name):
    """A required whole number. Accepts 7 or "7"; rejects "abc", 7.5, true and missing values."""
    value = data.get(name)
    if isinstance(value, bool):
        raise ApiError(400, f"'{name}' must be a whole number.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    raise ApiError(400, f"'{name}' must be a whole number.")


def str_field(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"'{name}' is required.")
    return value


def datetime_field(data, name):
    """A required date and time in ISO format, e.g. 2026-11-20T18:00."""
    try:
        return datetime.fromisoformat(str_field(data, name))
    except ValueError:
        raise ApiError(400, f"'{name}' must be a date and time like 2026-11-20T18:00.") from None


def init_app(app):
    @app.before_request
    def answer_preflight():
        # Browsers send OPTIONS before a cross-origin POST with JSON; answer it without running a route.
        if request.method == "OPTIONS":
            return "", 204

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response

    @app.errorhandler(ApiError)
    def api_error(error):
        return {"error": error.message}, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return {"error": error.description}, error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        log.exception("unhandled error")
        return {"error": "Something went wrong on our side. Please try again."}, 500
