"""Bookings service: accounts, courts and court bookings, as a JSON API.

Started in the container by: python migrate.py && gunicorn "app:create_app()"
"""
import os

from flask import Flask

import api
import observability
from accounts.routes import bp as accounts_bp
from bookings.routes import bp as bookings_bp


def create_app():
    app = Flask(__name__)
    observability.init_app(app)
    api.init_app(app)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(bookings_bp)
    return app


if __name__ == "__main__":
    # local run without Docker: python migrate.py && python app.py
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
