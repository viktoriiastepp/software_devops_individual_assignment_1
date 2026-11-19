// Where the browser finds the two services. This file is for local development with
// docker compose; the CD pipeline overwrites it with the Azure URLs before deploying the UI.
window.APP_CONFIG = {
  BOOKINGS_URL: "http://localhost:8001",
  MATCHMAKING_URL: "http://localhost:8002",
};
