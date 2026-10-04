# Architecture

Padel Matchmaker is one Flask process (`python app.py`) with three feature domains. Each domain owns its own tables and has the same layers: `routes.py` (web pages), `rules.py` (pure business rules, no database), `repository.py` (SQL).

## Architecture overview

```mermaid
flowchart TB
    browser["Browser"] -->|"HTTP on 0.0.0.0:PORT"| app

    subgraph process["One Python process: python app.py"]
        app["app.py<br/>create_app(), home, /health"]

        subgraph accounts["accounts domain"]
            a_routes["routes.py<br/>register, login, logout,<br/>login_required"]
            a_service["service.py<br/>password hashing"]
            a_rules["rules.py<br/>username / password rules"]
            a_repo["repository.py<br/>users"]
        end

        subgraph bookings["bookings domain"]
            b_routes["routes.py<br/>book, list, cancel"]
            b_rules["rules.py<br/>overlap, opening hours,<br/>late cancellation"]
            b_repo["repository.py<br/>courts, bookings"]
        end

        subgraph matchmaking["matchmaking domain"]
            m_routes["routes.py<br/>open, join, result,<br/>leaderboard"]
            m_rules["rules.py<br/>level window, balanced teams,<br/>Elo ratings"]
            m_repo["repository.py<br/>players, games, game_players"]
            m_lookup["booking_lookup.py<br/>(the seam)"]
        end

        db["db.py<br/>get_connection()"]
    end

    sqlite[("SQLite file<br/>DATA_DIR/padel.db")]

    app --> a_routes
    app --> b_routes
    app --> m_routes
    a_routes --> a_service --> a_rules
    a_service --> a_repo
    b_routes --> b_rules
    b_routes --> b_repo
    m_routes --> m_rules
    m_routes --> m_repo
    m_routes --> m_lookup
    m_lookup -.->|"only cross-domain call"| b_repo
    a_repo --> db
    b_repo --> db
    m_repo --> db
    db --> sqlite
```

The dashed arrow is the seam between matchmaking and bookings: `matchmaking/booking_lookup.py` is the only file in matchmaking that reads bookings data. If the domains become separate services, only that file changes into HTTP calls (ADR-2).

## Database schema

```mermaid
erDiagram
    users {
        INTEGER id PK
        TEXT username UK
        TEXT password_hash
        TEXT created_at
    }
    courts {
        INTEGER id PK
        TEXT name UK
    }
    bookings {
        INTEGER id PK
        INTEGER court_id FK
        INTEGER user_id
        TEXT start_time
        TEXT end_time
        TEXT status
        INTEGER cancelled_late
    }
    players {
        INTEGER id PK
        INTEGER user_id UK
        TEXT name
        INTEGER rating
    }
    games {
        INTEGER id PK
        INTEGER booking_id UK
        TEXT status
        INTEGER winning_team
    }
    game_players {
        INTEGER game_id PK, FK
        INTEGER player_id PK, FK
        INTEGER team
    }

    courts ||--o{ bookings : "court_id (foreign key)"
    games ||--o{ game_players : "game_id (foreign key)"
    players ||--o{ game_players : "player_id (foreign key)"
    users ||..o{ bookings : "user_id (no foreign key)"
    users ||..o| players : "user_id (no foreign key)"
    bookings ||..o| games : "booking_id (no foreign key, ADR-3)"
```

Solid lines are real foreign keys, used only inside one domain. Dashed lines are links between domains, stored as plain INTEGER ids with no foreign key, so each domain's tables could later move to their own database (ADR-3).

| Domain | Tables |
|---|---|
| accounts | users |
| bookings | courts, bookings |
| matchmaking | players, games, game_players |
