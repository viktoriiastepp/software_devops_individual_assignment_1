-- 001: bookings-service schema, ported from the Assignment 1 SQLite tables.
-- SQLite -> SQL Server: INTEGER PRIMARY KEY AUTOINCREMENT -> INT IDENTITY, TEXT -> NVARCHAR,
-- ISO date text -> DATETIME2, 0/1 integer -> BIT.

CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(20) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    created_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE courts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE bookings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    court_id INT NOT NULL REFERENCES courts(id),
    user_id INT NOT NULL,  -- accounts domain: plain id, no foreign key, as in Assignment 1
    start_time DATETIME2(0) NOT NULL,
    end_time DATETIME2(0) NOT NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    cancelled_late BIT NOT NULL DEFAULT 0,
    CHECK (end_time > start_time)
);

CREATE INDEX ix_bookings_court_status ON bookings (court_id, status);
CREATE INDEX ix_bookings_user ON bookings (user_id);
