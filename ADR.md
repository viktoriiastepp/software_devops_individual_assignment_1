# Architecture Decision Records

## 1. Backend language and framework: Python + Flask
Date: 2026-09-28
Status: Superseded by 7
Context: The app must run as a single process with SQLite, read its port and data directory from environment variables, and start with no manual setup. I also need to be able to explain every part of the code myself.
Decision: Use Python 3 with Flask, Python's built-in sqlite3 module instead of an ORM, and server-rendered Jinja templates for the frontend.
Alternatives considered: Django was rejected because its admin panel, ORM and migration system are features I don't need, and manual migrations conflict with the "no setup at startup" requirement. FastAPI was rejected because its main strengths (async, automatic JSON schemas) matter most for JSON APIs, while my app mainly serves HTML forms.
Consequences: I write SQL by hand and design the module structure myself, which takes more effort but keeps dependencies minimal and every query visible. Few dependencies also keep the container small for Assignment 2.

## 2. Splitting the app into Bookings and Matchmaking domains
Date: 2026-09-29
Status: Superseded by 6
Context: Court scheduling and player matching change for different reasons and are used by different stakeholders (club manager vs players). The app will be split into services in a later assignment, so the seam must exist now.
Decision: Two separate packages, bookings/ and matchmaking/, each owning its own tables and logic. Matchmaking refers to a game's court slot only by booking_id and never queries the bookings tables directly.
Alternatives considered: One shared models module with SQL joins across all tables, rejected because it would tie the domains together and force a rewrite of every cross-domain query when splitting them into services.
Consequences: No cross-domain JOINs, so a few lookups need two queries instead of one. In return, the matchmaking package could later run as its own service with only the booking lookup replaced by an HTTP call.

## 3. Linking matchmaking games to bookings by ID without a foreign key
Date: 2026-09-30
Status: Decided
Context: A matchmaking game needs a court slot, and court slots belong to the bookings domain. SQLite would let me add a FOREIGN KEY from games to bookings, but that would tie both domains to the same database.
Decision: Inside the bookings domain, bookings.court_id is a real foreign key to courts. The matchmaking games table will store booking_id as a plain INTEGER with no foreign key, and check that the booking exists through the bookings module's get_booking function.
Alternatives considered: A FOREIGN KEY from games.booking_id to bookings.id, rejected because the database would enforce a link across domains, and the tables could not be moved into separate services with their own databases without changing the schema.
Consequences: The database will not stop a game pointing at a missing booking, so the application must check it; bookings are cancelled with a status instead of deleted, which keeps that risk low. In return, each domain's tables can later live in its own database.

## 4. Testing approach: business rules first, then repositories, then routes
Date: 2026-10-03
Status: Superseded by 9
Context: The assignment requires at least 70% coverage of core business logic. The riskiest code is the booking rules, the Elo and team-balancing maths and the login checks, because a bug there silently gives wrong results instead of crashing.
Decision: Keep each domain's rules in pure functions with no database and test them first, including boundary cases (back-to-back slots, cancelling exactly 24 hours before, a rating exactly 150 points from the game level). Repositories and routes are tested against a fresh temporary SQLite database per test, with a fast password-hashing setting in tests only.
Alternatives considered: Testing mainly through the web pages with the Flask test client, rejected because a failing page test does not show which rule broke, and preparing four logged-in users for every rule check would make the tests slow and hard to read.
Consequences: Rules and repositories are at 100% coverage and fail precisely; route tests cover the main user flows but not every error message, and the HTML templates themselves are not checked.

## 5. Not building social login or password-reset emails
Date: 2026-10-04
Status: Decided
Context: After professor feedback the app needed a login system, so I had to decide how much authentication to build in the time left. Club members only need to identify themselves to book courts, join games and record results.
Decision: Build simple username and password accounts with hashed passwords and session cookies, and deliberately not build Google/social login or password reset by email.
Alternatives considered: Google sign-in (OAuth), rejected because it needs an external identity provider, client secrets and a public callback URL, which conflict with running locally in one container with no external runtime dependencies. Password-reset emails, rejected because they need an external email service.
Consequences: A member who forgets their password currently has no way to recover the account without an administrator. In exchange the app has no external dependency and stays deployable as a single container.

## 6. Splitting into a bookings service and a matchmaking service
Date: 2026-11-15
Status: Decided
Context: The monolith had three domains (accounts, bookings, matchmaking), but Assignment 2 allows exactly two service containers, each with its own database. ADR-2 had already kept every read of bookings data inside matchmaking/booking_lookup.py.
Decision: Two services. The bookings service owns accounts and bookings (users, courts, bookings tables) and issues a signed login token. The matchmaking service owns players, games and game_players, verifies the token with a shared secret, and gets booking data only by calling the bookings service over HTTP from bookings_client.py, the old booking_lookup.py. The cross-seam flow is server side: opening a game and listing open games need the booking's status, owner and court.
Alternatives considered: Accounts in the matchmaking service, rejected because checking who owns a booking is the core rule of the bookings domain and would then need a call on every booking. Joining the data in the browser, rejected because "only the owner can open a game on an active booking" must be checked on the server, where users cannot bypass it.
Consequences: ADR-2 held: only one file changes from function calls to HTTP calls. Matchmaking now depends on bookings being up, so every call has a 2-second timeout (BOOKINGS_TIMEOUT_S) and a designed fallback: listing games keeps working with the last booking details seen and a notice, while opening a game answers 503 with a clear message, because it must check the booking's current owner and status. The token secret must be the same in both services and is stored as a secret.

## 7. One SQL Server database per service, with versioned migrations
Date: 2026-11-16
Status: Decided
Context: ADR-1 used one SQLite file and created tables on first boot. Assignment 2 needs one SQL Server database per service, each reached with its own login, and schema changes applied in place once a database holds data. ADR-1's server-rendered pages are also replaced by a static UI, so ADR-1 is superseded; Flask and hand-written SQL stay.
Decision: The bookings database holds users, courts and bookings; the matchmaking database holds players, games and game_players. Each service's login is db_owner of its own database only. The schema lives in numbered files in services/<name>/migrations/, applied at startup by migrate.py, which records each version in schema_migrations, runs each file in one transaction and never edits an applied file. Types were ported (AUTOINCREMENT to INT IDENTITY, TEXT to NVARCHAR, ISO text to DATETIME2, 0/1 to BIT), and CHECK constraints now reject invalid status, team and winning_team values.
Alternatives considered: Alembic, rejected because it brings in SQLAlchemy for a codebase with no ORM, only to run SQL files in order; recreating tables on deploy, rejected because it destroys data.
Consequences: No production data had to move, because Assignment 1 was never deployed; the court seed data moved with its table. The links across the seam (games.booking_id, players.user_id) stay plain ids with no foreign key (ADR-3): matchmaking checks a booking over HTTP before creating a game and hides games whose booking is cancelled, and bookings are never deleted, so an id never points at a missing row. Migrations are forward only. Recovery plan for a bad migration in production: a failing file rolls back on its own and the previous version keeps running; a migration that succeeded but is wrong is fixed by redeploying the previous image and adding a new corrective migration; damaged data is recovered with Azure SQL point-in-time restore to just before the deploy.

## 9. Pipeline and testing: one GitHub Actions workflow, tests on a SQL Server container
Date: 2026-11-19
Status: Decided
Context: ADR-4 tested against a temporary SQLite file. The services now use SQL Server, and two services can break each other through the HTTP seam, which unit tests alone do not show. CI must never connect to Azure SQL, because every connection wakes the serverless database and is billed.
Decision: One workflow, ci-cd.yml, runs on every push and pull request: ruff; openapi-spec-validator on both openapi.yaml files plus a contract test that the endpoints matchmaking calls exist in the bookings document with the same Booking shape; each service's pytest suite against SQL Server started from the same docker-compose.yml used locally, with a 70% coverage gate per service; a Docker build of both images; and an integration job that starts the whole compose stack and runs tests/integration against both real services, including stopping the bookings container to check the degraded behaviour. Unit tests of matchmaking replace bookings_client with a stub (FakeBookings), so they test matchmaking's own rules; the real HTTP call is covered by test_bookings_client.py and by the integration job. Each service also checks that its openapi.yaml lists exactly the routes it serves. The CD jobs will be added to the same workflow and depend on all CI jobs, so a deploy can only follow a green CI run on the same commit.
Alternatives considered: A SQL Server service container in the workflow, rejected because it needs a second copy of the database setup and passwords next to the compose file; mocking the database, rejected because it would not catch T-SQL errors such as OUTPUT INSERTED or TOP; only a stubbed integration test, rejected because the compose stack is cheap in CI and also proves the timeouts and the 503 for real.
Consequences: A full run takes several minutes, mostly for SQL Server to start. Tests need a running SQL Server locally too (docker compose up -d db). The integration test stops a container, so it runs in its own job. ADR-4 is superseded.
