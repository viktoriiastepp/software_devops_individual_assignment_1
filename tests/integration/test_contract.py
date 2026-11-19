"""The endpoints matchmaking calls on bookings must exist in bookings' openapi.yaml with the same shapes."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(service):
    return yaml.safe_load((ROOT / "services" / service / "openapi.yaml").read_text(encoding="utf-8"))


def test_endpoints_called_by_matchmaking_exist_in_bookings_document():
    paths = load("bookings")["paths"]
    assert "get" in paths["/bookings/{booking_id}"]
    assert any(p["name"] == "ids" for p in paths["/bookings"]["get"]["parameters"])


def test_booking_shape_is_the_same_in_both_documents():
    assert load("bookings")["components"]["schemas"]["Booking"]["properties"].keys() == \
        load("matchmaking")["components"]["schemas"]["Booking"]["properties"].keys()
