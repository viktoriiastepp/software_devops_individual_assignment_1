-- 002: one-row table that GET /health updates and reads back, proving this service
-- can both write to and read from its own database.
CREATE TABLE health_probe (
    id INT NOT NULL PRIMARY KEY CHECK (id = 1),
    checked_at DATETIME2(0) NOT NULL
);

INSERT INTO health_probe (id, checked_at) VALUES (1, SYSUTCDATETIME());
