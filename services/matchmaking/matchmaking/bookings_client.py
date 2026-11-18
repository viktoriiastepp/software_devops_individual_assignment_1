"""The only place the matchmaking service talks to the bookings service (the seam from ADR-2/ADR-6).

Every call has a timeout. If bookings is down, slow or answers with a 5xx, calls raise
BookingsUnavailable, and callers choose a designed fallback: listing pages show the last booking
details seen (cached in memory), while actions that need fresh data answer 503 with a clear message.
"""
import os
import time

import requests
from flask import g, has_request_context, request

BOOKINGS_URL = os.environ.get("BOOKINGS_URL", "http://bookings:8000").rstrip("/")
TIMEOUT_S = float(os.environ.get("BOOKINGS_TIMEOUT_S", "2"))

# booking_id -> (booking, time it was fetched). One replica at most (ADR-8), so a process cache is enough.
_cache = {}


class BookingsUnavailable(Exception):
    """The bookings service could not answer in time."""


def _headers():
    """Forward the user's token (bookings checks it too) and the request id (to follow one request in both logs)."""
    if not has_request_context():
        return {}
    headers = {"X-Request-ID": g.get("request_id", "")}
    if "Authorization" in request.headers:
        headers["Authorization"] = request.headers["Authorization"]
    return headers


def _get(path, params=None):
    try:
        response = requests.get(BOOKINGS_URL + path, params=params, headers=_headers(), timeout=TIMEOUT_S)
    except requests.RequestException as error:  # timeout, refused connection, DNS failure...
        raise BookingsUnavailable(str(error)) from error
    if response.status_code >= 500:
        raise BookingsUnavailable(f"bookings answered {response.status_code}")
    return response


def _remember(booking):
    _cache[booking["id"]] = (booking, time.time())


def get_booking(booking_id):
    """The booking with this id, or None if it does not exist. Raises BookingsUnavailable."""
    response = _get(f"/bookings/{booking_id}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    booking = response.json()
    _remember(booking)
    return booking


def get_bookings(booking_ids):
    """Return ({id: booking}, stale). stale is True when bookings was down and cached details were used."""
    if not booking_ids:
        return {}, False
    try:
        response = _get("/bookings", params={"ids": ",".join(str(i) for i in booking_ids)})
        response.raise_for_status()
    except (BookingsUnavailable, requests.HTTPError):
        return {i: _cache[i][0] for i in booking_ids if i in _cache}, True
    bookings = {b["id"]: b for b in response.json()["bookings"]}
    for booking in bookings.values():
        _remember(booking)
    return bookings, False
