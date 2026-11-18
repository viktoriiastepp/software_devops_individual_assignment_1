-- 003: the club's six courts. Seed data lives in a migration, so it is inserted exactly once,
-- even when several workers start at the same time.
INSERT INTO courts (name)
SELECT name FROM (VALUES ('Court 1'), ('Court 2'), ('Court 3'), ('Court 4'), ('Court 5'), ('Court 6')) AS seed(name)
WHERE NOT EXISTS (SELECT 1 FROM courts WHERE courts.name = seed.name);
