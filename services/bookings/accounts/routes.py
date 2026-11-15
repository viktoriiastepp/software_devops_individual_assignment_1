from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from accounts import service

bp = Blueprint("accounts", __name__)


def login_required(view):
    """Decorator: send visitors who are not logged in to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("accounts.login"))
        return view(*args, **kwargs)
    return wrapped


def start_session(user_id, username):
    session.clear()
    session["user_id"] = user_id
    session["username"] = username


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id, errors = service.register(request.form["username"], request.form["password"])
        if not errors:
            start_session(user_id, service.normalise(request.form["username"]))
            return redirect(url_for("home"))
        for error in errors:
            flash(error)
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = service.authenticate(request.form["username"], request.form["password"])
        if user:
            start_session(user["id"], user["username"])
            return redirect(url_for("home"))
        flash("Wrong username or password.")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("accounts.login"))
