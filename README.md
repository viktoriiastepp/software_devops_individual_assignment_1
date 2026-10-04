# Padel Matchmaker

A web app for a padel club that handles court bookings and forms balanced matches between players of a similar level.

## The problem
At a busy club (6 courts, around 400 members of mixed levels), players struggle to find three others at a similar level. Courts sit empty, or matches end up one-sided and nobody enjoys them.

## Stakeholders
- The club manager, who wants courts used efficiently and no double bookings
- Club members, who want fair, competitive games without organising them in group chats

## Feature domains
1. **Bookings**: 6 courts, 90-minute slots between 08:00 and 23:00. Rejects overlapping bookings, bookings in the past and bookings outside opening hours. Cancellations less than 24 hours before are flagged as late.
2. **Matchmaking**: a player opens a game on their booking. Others can join only if their rating is within 150 points of the game's average. When the fourth player joins, the app picks the most balanced 2v2 split. After the result, every rating is updated with the Elo formula.
3. **Accounts**: register, log in and log out. Passwords are stored as hashes, never as plain text.

## Requirements
- Python 3.10 or newer

## Setup and run
```bash
git clone https://github.com/viktoriiastepp/software_devops_individual_assignment_1.git
cd software_devops_individual_assignment_1
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Then open http://localhost:8080 and register an account. No other setup is needed: the database and all tables are created automatically on startup.

To try a full game you need four accounts, for example in four private browser windows.

## Configuration
All configuration comes from environment variables. None are required.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Port the app listens on (always bound to `0.0.0.0`) |
| `DATA_DIR` | `./data` | Folder for the SQLite file; created if missing |
| `SECRET_KEY` | random on each start | Signs login sessions. Set it in production, otherwise everyone is logged out when the app restarts |

Example: `PORT=9000 DATA_DIR=/tmp/padel SECRET_KEY=change-me python app.py`

## Database
SQLite file at **`DATA_DIR/padel.db`** (by default `./data/padel.db`). Delete the file to start with an empty database.

## Tests and coverage
```bash
pytest --cov=accounts --cov=bookings --cov=matchmaking --cov-report=term-missing
```
Result on 2026-10-04: **57 passed, 98% total coverage**. Every `rules.py` (business logic) and `repository.py` file is at 100%; the only uncovered lines are rare error branches in the route files.

## Health check
`GET /health` returns `{"status": "ok"}`.

## Documentation
- [ADR.md](ADR.md): the five architecture decisions
- [AI_USAGE.md](AI_USAGE.md): AI usage log
- [docs/architecture.md](docs/architecture.md): architecture and database diagrams
