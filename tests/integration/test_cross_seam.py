"""Integration tests across the seam, run against the real docker compose stack (see ADR-9).

Start the stack first: docker compose up -d --build
Then run from the repository root: pytest -q tests/integration
"""
import os
import random
import subprocess
import time
import uuid
from datetime import datetime, timedelta

import pytest
import requests

BOOKINGS = os.environ.get("BOOKINGS_URL", "http://localhost:8001")
MATCHMAKING = os.environ.get("MATCHMAKING_URL", "http://localhost:8002")


def register():
    name = "it_" + uuid.uuid4().hex[:8]
    response = requests.post(f"{BOOKINGS}/auth/register", json={"username": name, "password": "smash2026"}, timeout=10)
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def book_a_court(headers):
    """Book a free slot; random court and day so repeated runs on the same database do not overlap."""
    for _ in range(20):
        day = datetime.now() + timedelta(days=random.randint(2, 300))
        start = day.replace(hour=random.choice([8, 10, 12, 14, 16, 18, 20]), minute=0).strftime("%Y-%m-%dT%H:%M")
        response = requests.post(
            f"{BOOKINGS}/bookings", json={"court_id": random.randint(1, 6), "start_time": start}, headers=headers, timeout=10
        )
        if response.status_code == 201:
            return response.json()
    pytest.fail("could not find a free slot")


def wait_until_healthy(url, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if requests.get(url + "/health", timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    pytest.fail(f"{url} did not become healthy")


def test_opening_a_game_checks_the_booking_in_the_bookings_service():
    ana, ben = register(), register()
    booking = book_a_court(ana)

    # matchmaking calls GET /bookings/{id} on the bookings service, server side
    created = requests.post(f"{MATCHMAKING}/games", json={"booking_id": booking["id"]}, headers=ana, timeout=10)
    assert created.status_code == 201, created.text
    assert created.json()["booking"]["court_name"] == booking["court_name"]

    # someone else's booking is refused by the same cross-seam check
    other = book_a_court(ben)
    refused = requests.post(f"{MATCHMAKING}/games", json={"booking_id": other["id"]}, headers=ana, timeout=10)
    assert refused.status_code == 403

    # a cancelled booking hides its game from the open list (GET /bookings?ids=...)
    requests.post(f"{BOOKINGS}/bookings/{booking['id']}/cancel", headers=ana, timeout=10)
    open_ids = [g["id"] for g in requests.get(f"{MATCHMAKING}/games/open", headers=ana, timeout=10).json()["games"]]
    assert created.json()["id"] not in open_ids


def test_matchmaking_degrades_when_bookings_is_stopped():
    ana = register()
    booking = book_a_court(ana)
    game = requests.post(f"{MATCHMAKING}/games", json={"booking_id": booking["id"]}, headers=ana, timeout=10).json()
    second = book_a_court(ana)

    subprocess.run(["docker", "compose", "stop", "bookings"], check=True)
    try:
        started = time.time()
        listing = requests.get(f"{MATCHMAKING}/games/open", headers=ana, timeout=10)
        assert listing.status_code == 200
        assert listing.json()["notice"]  # booking details come from the cache, with a notice
        assert game["id"] in [g["id"] for g in listing.json()["games"]]

        blocked = requests.post(f"{MATCHMAKING}/games", json={"booking_id": second["id"]}, headers=ana, timeout=10)
        assert blocked.status_code == 503
        assert "unavailable" in blocked.json()["error"]

        assert requests.get(f"{MATCHMAKING}/health", timeout=5).status_code == 200  # its own health is unaffected
        assert time.time() - started < 8  # timeouts keep every answer quick
    finally:
        subprocess.run(["docker", "compose", "start", "bookings"], check=True)
        wait_until_healthy(BOOKINGS)
