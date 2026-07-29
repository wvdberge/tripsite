# CLAUDE.md — tripsite

Guidance for a future Claude session working on this codebase. Read `PLAN.md`
for the original design; read `tech_setup/Tripsite-Setup.md` (in the `personal`
repo) for deploy/backup/restore, including how to migrate the live NAS DB.

## What this is

A private, LAN-only trip-planning web app holding **many trips at once** (NZ
2027, UK Cycling 2026, and whatever comes next). Flask + SQLite + Jinja2 + htmx +
Leaflet. Two users (Wiljan + Annick), no passwords (a name-picker cookie stamps
authorship and feed events). Runs in one Docker container on the Synology NAS at
`http://192.168.1.202:8027`. The **SQLite DB is the source of truth**, not the
markdown files in `../new_zealand_2027/` and `../uk_cycling/` (those were imported
once). The repo lives at `~/personal/vakantie/tripsite/` (its own git remote,
`wvdberge/tripsite`, gitignored inside the `personal` repo).

## Architecture in one screen

- `app.py` — all routes + helpers. `db.py` — connection, schema init, event log.
  `schema.sql` — tables (`PRAGMA user_version = 2`). `migrate_v2.py` — one-time
  v1→v2 migration for an existing DB. `seed_trip.py` + `seed/trips/<name>.py` —
  per-trip seed data. `seed/places.py` — name→lat/lon. `templates/` (Jinja +
  htmx), `static/` (vendored htmx + Leaflet).
- **The active trip is a cookie** (`trip_id`), resolved in `app.py resolve_trip`:
  the cookie if valid, else the next upcoming trip (end_date >= today, earliest
  start), else the most recent one. People are **global** (shared across trips).
- **Every read is scoped by `g.trip["id"]`.** Every list/detail query filters by
  `trip_id`; routes that fetch by primary key also add `AND trip_id = ?` so a
  stale URL from another trip 404s.
- **Every write appends one `event`** with a human-readable summary (the feed),
  scoped to its trip. Keep summaries in the code path, don't reconstruct from data.
- **A day's leg is derived by date**, not a FK: `start_date <= date < end_date`
  within the trip (`leg_for_date`). Pre-arrival and departure days have no leg.
- **Money:** each trip has `currency` (its local code) and `fx_to_eur` (EUR per 1
  unit). Each cost stores EUR or the trip's local currency; roll-ups convert to
  EUR via `to_eur`. NZ = NZD/0.56, UK = GBP/1.1711. No live FX.
- **htmx** returns small partials (`_idea_status.html`, `_task_item.html`) for
  inline swaps; everything else is plain forms + redirects.

## Adding a trip = write a seed module, never wipe

**Standing decision from Wiljan: every past trip stays in the app; a new trip is
added additively, never by wiping and replacing.** The app is already multi-trip,
so adding one is now small:

1. Write `seed/trips/<name>.py` exporting `TRIP, LEGS, COSTS, TASKS, IDEAS`
   (copy the tuple formats and header from `nz2027.py` / `uk2026.py`). Add any
   new place coordinates to `seed/places.py`.
2. Run `./.venv/bin/python seed_trip.py <name>` (honors `TRIPSITE_DB`). It inserts
   the trip + legs + days + costs + tasks + ideas additively, creates missing
   people but never duplicates them, and **refuses if a trip with that name
   already exists** (so a re-run is a safe no-op, not a duplicate).

Or use the in-app **create-trip form** at `/trips` for an empty trip (name,
dates, currency, fx, budget); it generates the day rows and you fill the rest
through the UI. There is no wipe tool; a from-scratch rebuild is just
`seed_trip.py nz2027 --partner "Annick"` then `seed_trip.py uk2026` on an empty DB.

## Working on it

- Local: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`,
  seed (above), then `./.venv/bin/python app.py` (http://127.0.0.1:5000, or a free
  port — macOS AirPlay often holds 5000). DB path is `TRIPSITE_DB` (defaults to
  `./data/trip.db`).
- **Migrating an existing (v1) DB:** back it up, then `./.venv/bin/python
  migrate_v2.py`. It is idempotent (a second run no-ops) and reports row counts +
  a foreign-key check. New code against an unmigrated DB will 500 (it reads
  `trip.currency` and `UNIQUE(trip_id,date)`), so migrate before trusting the app.
- Deploy is git-clone-on-NAS + `sudo docker compose up -d --build` (see
  `tech_setup/Tripsite-Setup.md`). NAS gotchas: Docker needs sudo; scp/SFTP is
  disabled (write files with `ssh 'cat > file'`); the compose build uses
  `network: host` to get past Synology's bridge-DNS failure during `pip install`.
