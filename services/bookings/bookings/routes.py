from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from accounts.routes import login_required
from bookings import repository, rules

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


def to_datetime(text):
    return datetime.fromisoformat(text)


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    courts = repository.list_courts()
    court_names = {court["id"]: court["name"] for court in courts}

    if request.method == "POST":
        try:
            court_id = int(request.form["court_id"])
            start = to_datetime(request.form["start_time"])
        except (KeyError, ValueError):
            flash("Please choose a court and a valid date and time.")
            return redirect(url_for("bookings.index"))

        if court_id not in court_names:
            flash("That court does not exist.")
            return redirect(url_for("bookings.index"))

        existing = [
            (to_datetime(b["start_time"]), to_datetime(b["end_time"]))
            for b in repository.active_bookings_for_court(court_id)
        ]
        errors = rules.validate_new_booking(start, datetime.now(), existing)
        if errors:
            for error in errors:
                flash(error)
        else:
            repository.create_booking(court_id, session["user_id"], start, rules.end_time_for(start))
            flash("Court booked.", "success")
        return redirect(url_for("bookings.index"))

    my_bookings = repository.bookings_for_user(session["user_id"])
    return render_template("bookings.html", courts=courts, court_names=court_names, bookings=my_bookings)


@bp.route("/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id):
    booking = repository.get_booking(booking_id)
    if booking is None or booking["user_id"] != session["user_id"] or booking["status"] != "active":
        flash("You can only cancel your own active bookings.")
        return redirect(url_for("bookings.index"))

    late = rules.is_late_cancellation(to_datetime(booking["start_time"]), datetime.now())
    repository.cancel_booking(booking_id, late)
    if late:
        flash("Booking cancelled. This counts as a late cancellation (less than 24 hours before).", "success")
    else:
        flash("Booking cancelled.", "success")
    return redirect(url_for("bookings.index"))
