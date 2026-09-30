import os

from flask import Flask

from bookings import repository as bookings_repository

# Port comes from an environment variable with a safe default
PORT = int(os.environ.get("PORT", "8080"))


def create_app():
    bookings_repository.init_schema()  # tables are created automatically at startup, no manual migration

    app = Flask(__name__)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    # 0.0.0.0 so it works inside a container; debug off keeps it to one process
    create_app().run(host="0.0.0.0", port=PORT, debug=False)
