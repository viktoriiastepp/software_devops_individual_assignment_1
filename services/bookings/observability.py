"""Request logging and GET /health, registered on the Flask app of each service."""
import logging
import os
import sys
import time
import uuid

from flask import g, request

import db

log = logging.getLogger("access")

# Set by the pipeline to the git commit SHA, so /health shows which build is running.
VERSION = os.environ.get("APP_VERSION", "dev")


def init_app(app):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()
        # Reuse the caller's id so one request can be followed across both services' logs.
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
        request_id = g.get("request_id", "-")
        response.headers["X-Request-ID"] = request_id
        log.info(
            "method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
            request.method, request.path, response.status_code, duration_ms, request_id,
        )
        return response

    @app.get("/health")
    def health():
        """200 when this service can read and write its own database, 503 otherwise."""
        try:
            # one attempt only: /health must answer quickly, the caller decides whether to retry
            with db.transaction(attempts=1) as cursor:
                # one real write and one read on this service's own database (table from migration 002)
                cursor.execute("UPDATE health_probe SET checked_at = SYSUTCDATETIME() WHERE id = 1")
                cursor.execute("SELECT checked_at FROM health_probe WHERE id = 1")
                if cursor.fetchone() is None:
                    raise RuntimeError("health_probe row missing")
        except Exception as error:  # any database failure means the service is not healthy
            log.warning("health check failed: %s", error)
            return {"status": "error", "db": "unreachable", "version": VERSION}, 503
        return {"status": "ok", "db": "ok", "version": VERSION}, 200
