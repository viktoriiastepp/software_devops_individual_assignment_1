"""Courts and bookings. GET routes only read; every input is validated before use."""
from datetime import datetime

from flask import Blueprint, g, request

from api import ApiError, datetime_field, int_field, json_body
from auth import require_user
from bookings import repository, rules

bp = Blueprint("bookings", __name__)

MAX_IDS_PER_LOOKUP = 100


def to_json(booking):
    """The booking shape both the UI and the matchmaking service rely on (see openapi.yaml)."""
    return {
        "id": booking["id"],
        "court_id": booking["court_id"],
        "court_name": booking["court_name"],
        "user_id": booking["user_id"],
        "start_time": booking["start_time"].isoformat(timespec="minutes"),
        "end_time": booking["end_time"].isoformat(timespec="minutes"),
        "status": booking["status"],
        "cancelled_late": bool(booking["cancelled_late"]),
    }


@bp.get("/courts")
def list_courts():
    return {"courts": [{"id": c["id"], "name": c["name"]} for c in repository.list_courts()]}


@bp.get("/bookings/mine")
@require_user
def my_bookings():
    return {"bookings": [to_json(b) for b in repository.bookings_for_user(g.user_id)]}


@bp.post("/bookings")
@require_user
def create_booking():
    data = json_body()
    court_id = int_field(data, "court_id")
    start = datetime_field(data, "start_time").replace(second=0, microsecond=0, tzinfo=None)
    if court_id not in {c["id"] for c in repository.list_courts()}:
        raise ApiError(400, "That court does not exist.")

    existing = [(b["start_time"], b["end_time"]) for b in repository.active_bookings_for_court(court_id)]
    errors = rules.validate_new_booking(start, datetime.now(), existing)
    if errors:
        return {"error": errors[0], "errors": errors}, 400
    booking_id = repository.create_booking(court_id, g.user_id, start, rules.end_time_for(start))
    return to_json(repository.get_booking(booking_id)), 201


@bp.post("/bookings/<int:booking_id>/cancel")
@require_user
def cancel_booking(booking_id):
    booking = repository.get_booking(booking_id)
    if booking is None:
        raise ApiError(404, "Booking not found.")
    if booking["user_id"] != g.user_id:
        raise ApiError(403, "You can only cancel your own bookings.")
    if booking["status"] != "active":
        raise ApiError(409, "This booking is already cancelled.")
    late = rules.is_late_cancellation(booking["start_time"], datetime.now())
    repository.cancel_booking(booking_id, late)
    return to_json(repository.get_booking(booking_id))


# --- read by the matchmaking service (cross-seam calls, see system.yaml) ---

@bp.get("/bookings/<int:booking_id>")
@require_user
def get_booking(booking_id):
    booking = repository.get_booking(booking_id)
    if booking is None:
        raise ApiError(404, "Booking not found.")
    return to_json(booking)


@bp.get("/bookings")
@require_user
def get_bookings_by_ids():
    """GET /bookings?ids=1,2,3: several bookings in one call, so listing games is one request, not N."""
    raw = request.args.get("ids", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts or not all(p.isdigit() for p in parts) or len(parts) > MAX_IDS_PER_LOOKUP:
        raise ApiError(400, f"'ids' must be 1 to {MAX_IDS_PER_LOOKUP} comma-separated booking ids.")
    return {"bookings": [to_json(b) for b in repository.get_bookings(sorted({int(p) for p in parts}))]}
