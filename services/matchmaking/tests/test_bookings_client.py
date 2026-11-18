"""The HTTP call across the seam, with requests.get replaced so no network is needed."""
import pytest
import requests

from matchmaking import bookings_client

BOOKING = {"id": 7, "court_id": 1, "court_name": "Court 1", "user_id": 1, "status": "active"}


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


@pytest.fixture
def calls(monkeypatch):
    """Record each outgoing call; tests set calls.answer to a response or an exception."""
    class Calls(list):
        answer = None
    recorded = Calls()

    def fake_get(url, params=None, headers=None, timeout=None):
        recorded.append({"url": url, "params": params, "timeout": timeout})
        if isinstance(recorded.answer, Exception):
            raise recorded.answer
        return recorded.answer

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(bookings_client, "_cache", {})
    return recorded


def test_every_call_has_the_configured_timeout(calls):
    calls.answer = FakeResponse(200, BOOKING)
    bookings_client.get_booking(7)
    assert calls[0]["timeout"] == bookings_client.TIMEOUT_S
    assert calls[0]["url"].endswith("/bookings/7")


def test_missing_booking_is_none(calls):
    calls.answer = FakeResponse(404, {"error": "Booking not found."})
    assert bookings_client.get_booking(7) is None


@pytest.mark.parametrize("answer", [requests.ConnectTimeout("slow"), requests.ConnectionError("refused"), FakeResponse(503)])
def test_timeouts_refusals_and_5xx_raise_bookings_unavailable(calls, answer):
    calls.answer = answer
    with pytest.raises(bookings_client.BookingsUnavailable):
        bookings_client.get_booking(7)


def test_listing_uses_cached_details_when_bookings_goes_down(calls):
    calls.answer = FakeResponse(200, {"bookings": [BOOKING]})
    assert bookings_client.get_bookings([7]) == ({7: BOOKING}, False)
    assert calls[0]["params"] == {"ids": "7"}

    calls.answer = requests.ReadTimeout("slow")
    assert bookings_client.get_bookings([7, 8]) == ({7: BOOKING}, True)


def test_empty_list_makes_no_call(calls):
    assert bookings_client.get_bookings([]) == ({}, False)
    assert calls == []
