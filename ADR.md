# Architecture Decision Records

## 1. Backend language and framework: Python + Flask
Date: 2026-09-28
Status: Decided
Context: The app must run as a single process with SQLite, read its port and data directory from environment variables, and start with no manual setup. I also need to be able to explain every part of the code myself.
Decision: Use Python 3 with Flask, Python's built-in sqlite3 module instead of an ORM, and server-rendered Jinja templates for the frontend.
Alternatives considered: Django was rejected because its admin panel, ORM and migration system are features I don't need, and manual migrations conflict with the "no setup at startup" requirement. FastAPI was rejected because its main strengths (async, automatic JSON schemas) matter most for JSON APIs, while my app mainly serves HTML forms.
Consequences: I write SQL by hand and design the module structure myself, which takes more effort but keeps dependencies minimal and every query visible. Few dependencies also keep the container small for Assignment 2.
