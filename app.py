import os
import secrets

from flask import Flask, render_template, session

from accounts import repository as accounts_repository
from accounts.routes import bp as accounts_bp
from accounts.routes import login_required
from bookings import repository as bookings_repository
from matchmaking import repository as matchmaking_repository

PORT = int(os.environ.get("PORT", "8080"))


def create_app():
    # each domain creates its own tables, so no manual migration is needed
    accounts_repository.init_schema()
    bookings_repository.init_schema()
    matchmaking_repository.init_schema()

    app = Flask(__name__)
    # sessions are signed with this key; without SECRET_KEY set, a random one is used
    # and everyone is logged out when the app restarts
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.register_blueprint(accounts_bp)

    @app.route("/")
    @login_required
    def home():
        return render_template("home.html", username=session["username"])

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=PORT, debug=False)
