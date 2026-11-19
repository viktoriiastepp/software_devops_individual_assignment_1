// Static UI for the two services. It only calls their JSON APIs; it holds no data of its own
// apart from the login token, which it keeps in localStorage and sends as a Bearer header.
"use strict";

const CONFIG = window.APP_CONFIG || {};
const BOOKINGS = (CONFIG.BOOKINGS_URL || "").replace(/\/$/, "");
const MATCHMAKING = (CONFIG.MATCHMAKING_URL || "").replace(/\/$/, "");
const SESSION_KEY = "padel-session";
const $ = (id) => document.getElementById(id);

// --- session -----------------------------------------------------------------

function loadSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY));
  } catch {
    return null;
  }
}

function saveSession(session) {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    // storage blocked: the session then lasts until the page is reloaded
  }
  state.session = session;
}

const state = { session: loadSession() };

// --- HTTP --------------------------------------------------------------------

async function api(base, path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.session) headers.Authorization = "Bearer " + state.session.token;
  let response;
  try {
    response = await fetch(base + path, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new Error("The service could not be reached. Please try again in a minute.");
  }
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && state.session) {
    saveSession(null);
    route();
  }
  if (!response.ok) throw new Error(data.error || "Request failed (" + response.status + ").");
  return data;
}

// --- small helpers -----------------------------------------------------------

function showMessage(text, kind = "error") {
  const box = $("message");
  box.textContent = text;
  box.className = kind === "success" ? "flash success" : "flash";
  box.hidden = !text;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function button(label, onClick, secondary = false) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  if (secondary) b.className = "secondary";
  b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      await onClick();
    } catch (error) {
      showMessage(error.message);
    } finally {
      b.disabled = false;
    }
  });
  return b;
}

function row(cells, actions = null) {
  const tr = document.createElement("tr");
  cells.forEach((text) => tr.appendChild(cell(text)));
  if (actions) {
    const td = document.createElement("td");
    td.className = "actions";
    actions.forEach((a) => td.appendChild(a));
    tr.appendChild(td);
  }
  return tr;
}

function emptyRow(body, columns, text) {
  const tr = document.createElement("tr");
  const td = cell(text);
  td.colSpan = columns;
  td.className = "hint";
  tr.appendChild(td);
  body.replaceChildren(tr);
}

function when(booking) {
  if (!booking) return "unavailable";
  const [day, time] = booking.start_time.split("T");
  return day + " " + time + "–" + booking.end_time.split("T")[1];
}

function teams(players) {
  const names = (team) => players.filter((p) => p.team === team).map((p) => p.name).join(" & ");
  return players.some((p) => p.team) ? names(1) + " vs " + names(2) : players.map((p) => p.name).join(", ");
}

// --- views -------------------------------------------------------------------

async function showBookings() {
  const [{ courts }, { bookings }, mine] = await Promise.all([
    api(BOOKINGS, "/courts"),
    api(BOOKINGS, "/bookings/mine"),
    api(MATCHMAKING, "/games/mine").catch(() => ({ games: [] })),
  ]);
  $("court-select").replaceChildren(...courts.map((c) => new Option(c.name, c.id)));

  const withGame = new Set(mine.games.map((g) => g.booking_id));
  const body = $("bookings-body");
  if (!bookings.length) return emptyRow(body, 4, "No bookings yet.");
  body.replaceChildren(
    ...bookings.map((b) => {
      const actions = [];
      if (b.status === "active") {
        if (!withGame.has(b.id)) {
          actions.push(button("Open game", async () => {
            await api(MATCHMAKING, "/games", { method: "POST", body: { booking_id: b.id } });
            showMessage("Game opened. Other players can now join it.", "success");
            location.hash = "#games";
          }));
        }
        actions.push(button("Cancel", async () => {
          const result = await api(BOOKINGS, "/bookings/" + b.id + "/cancel", { method: "POST" });
          showMessage(result.cancelled_late ? "Cancelled (late: less than 24 hours before)." : "Booking cancelled.", "success");
          await showBookings();
        }, true));
      }
      const status = b.status === "cancelled" && b.cancelled_late ? "cancelled (late)" : b.status;
      return row([b.court_name, when(b), status], actions);
    }),
  );
}

async function showGames() {
  const [open, mine] = await Promise.all([api(MATCHMAKING, "/games/open"), api(MATCHMAKING, "/games/mine")]);
  const notice = open.notice || mine.notice;
  $("games-notice").textContent = notice || "";
  $("games-notice").hidden = !notice;

  const myGameIds = new Set(mine.games.map((g) => g.id));
  const openBody = $("open-games-body");
  if (!open.games.length) emptyRow(openBody, 5, "No open games. Open one from a booking.");
  else
    openBody.replaceChildren(
      ...open.games.map((g) => {
        const actions = myGameIds.has(g.id) ? [] : [button("Join", async () => {
          await api(MATCHMAKING, "/games/" + g.id + "/join", { method: "POST" });
          showMessage("You joined the game.", "success");
          await showGames();
        })];
        const court = g.booking ? g.booking.court_name : "Court unavailable";
        return row([court, when(g.booking), String(g.level), g.players.length + "/4"], actions);
      }),
    );

  const myBody = $("my-games-body");
  if (!mine.games.length) return emptyRow(myBody, 5, "You have not joined any games yet.");
  myBody.replaceChildren(
    ...mine.games.map((g) => {
      const actions = [];
      if (g.status === "full") {
        [1, 2].forEach((team) => actions.push(button("Team " + team + " won", async () => {
          await api(MATCHMAKING, "/games/" + g.id + "/result", { method: "POST", body: { winning_team: team } });
          showMessage("Result saved. Ratings updated.", "success");
          await showGames();
        }, team === 2)));
      }
      const status = g.status === "finished" ? "finished (team " + g.winning_team + " won)" : g.status;
      return row([g.booking ? g.booking.court_name : "Court unavailable", when(g.booking), status, teams(g.players)], actions);
    }),
  );
}

async function showLeaderboard() {
  const [{ players }, me] = await Promise.all([api(MATCHMAKING, "/leaderboard"), api(MATCHMAKING, "/players/me")]);
  $("my-rating").textContent = "Your rating: " + me.rating;
  const body = $("leaderboard-body");
  if (!players.length) return emptyRow(body, 3, "No ratings yet. Finish a game to appear here.");
  body.replaceChildren(...players.map((p, i) => row([String(i + 1), p.name, String(p.rating)])));
}

const VIEWS = { bookings: showBookings, games: showGames, leaderboard: showLeaderboard };

async function route() {
  const loggedIn = Boolean(state.session);
  const name = loggedIn ? (location.hash.slice(1) in VIEWS ? location.hash.slice(1) : "bookings") : "login";
  document.querySelectorAll("main section").forEach((s) => (s.hidden = s.id !== "view-" + name));
  $("nav").hidden = !loggedIn;
  $("logout").hidden = !loggedIn;
  $("who").textContent = loggedIn ? state.session.user.username : "";
  if (VIEWS[name]) {
    try {
      await VIEWS[name]();
    } catch (error) {
      showMessage(error.message);
    }
  }
}

// --- forms -------------------------------------------------------------------

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const action = event.submitter ? event.submitter.dataset.action : "login";
  const form = new FormData(event.target);
  try {
    const session = await api(BOOKINGS, "/auth/" + action, {
      method: "POST",
      body: { username: form.get("username"), password: form.get("password") },
    });
    saveSession(session);
    event.target.reset();
    showMessage("");
    location.hash = "#bookings";
    await route();
  } catch (error) {
    showMessage(error.message);
  }
});

$("booking-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api(BOOKINGS, "/bookings", {
      method: "POST",
      body: { court_id: Number(form.get("court_id")), start_time: form.get("start_time") },
    });
    showMessage("Court booked.", "success");
    await showBookings();
  } catch (error) {
    showMessage(error.message);
  }
});

$("logout").addEventListener("click", () => {
  saveSession(null);
  showMessage("");
  location.hash = "";
  route();
});

window.addEventListener("hashchange", () => {
  showMessage("");
  route();
});
route();
