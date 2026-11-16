-- 001: matchmaking-service schema, ported from the Assignment 1 SQLite tables.
-- user_id (accounts) and booking_id (bookings) live in the other service's database,
-- so they are plain ids with no foreign key (ADR-3); the code checks them over HTTP.

CREATE TABLE players (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    name NVARCHAR(20) NOT NULL,
    rating INT NOT NULL DEFAULT 1000
);

CREATE TABLE games (
    id INT IDENTITY(1,1) PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    status NVARCHAR(10) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'full', 'finished')),
    winning_team INT NULL CHECK (winning_team IN (1, 2))
);

CREATE TABLE game_players (
    game_id INT NOT NULL REFERENCES games(id),
    player_id INT NOT NULL REFERENCES players(id),
    team INT NULL CHECK (team IN (1, 2)),
    PRIMARY KEY (game_id, player_id)
);
