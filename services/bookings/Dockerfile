# Image for the bookings service. Built by docker compose locally and by CI; it never contains secrets:
# DATABASE_URL, TOKEN_SECRET and the rest are given as environment variables when the container starts.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# dependencies first: this layer is reused from cache until requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# only the files the service needs, named one by one (no COPY . .)
COPY app.py api.py auth.py db.py migrate.py observability.py ./
COPY migrations/ migrations/
COPY accounts/ accounts/
COPY bookings/ bookings/

# run as an unprivileged user, never as root
RUN useradd --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8000

# apply pending migrations once, then start gunicorn with one worker and 8 threads (exec: gunicorn receives the stop signal);
# one process keeps the fallback cache of booking details in one place.
# --timeout 120 leaves room for a paused Azure database to resume on the first request.
CMD ["sh", "-c", "python migrate.py && exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 120 'app:create_app()'"]
