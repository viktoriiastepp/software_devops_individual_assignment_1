-- Local development only: creates one database and one login per service.
-- Safe to run many times: every statement checks first whether the object exists.
-- Passwords come in as sqlcmd variables from docker-compose.yml, never hardcoded here.

IF DB_ID('bookings') IS NULL CREATE DATABASE bookings;
GO
IF DB_ID('matchmaking') IS NULL CREATE DATABASE matchmaking;
GO

IF SUSER_ID('bookings_app') IS NULL
    CREATE LOGIN bookings_app WITH PASSWORD = '$(BOOKINGS_DB_PASSWORD)';
GO
IF SUSER_ID('matchmaking_app') IS NULL
    CREATE LOGIN matchmaking_app WITH PASSWORD = '$(MATCHMAKING_DB_PASSWORD)';
GO

-- Each login becomes owner of its own database only, so it can run its own migrations
-- but cannot even open the other service's database.
USE bookings;
IF USER_ID('bookings_app') IS NULL CREATE USER bookings_app FOR LOGIN bookings_app;
ALTER ROLE db_owner ADD MEMBER bookings_app;
GO

USE matchmaking;
IF USER_ID('matchmaking_app') IS NULL CREATE USER matchmaking_app FOR LOGIN matchmaking_app;
ALTER ROLE db_owner ADD MEMBER matchmaking_app;
GO
