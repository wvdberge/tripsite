# CLAUDE.md — tripsite

Guidance for a future Claude session working on this codebase. Read `PLAN.md`
for the original design and locked decisions; read `tech_setup/Tripsite-Setup.md`
(in the `personal` repo) for deploy/backup/restore.

## What this is

A private, LAN-only trip-planning web app. Flask + SQLite + Jinja2 + htmx +
Leaflet. Two users (Wiljan + Annick), no passwords (a name-picker cookie stamps
authorship and feed events). Runs in one Docker container on the Synology NAS at
`http://192.168.1.202:8027`. The **SQLite DB is the source of truth**, not the
markdown files in `../` (those were imported once).

## Architecture in one screen

- `app.py` — all routes + helpers. `db.py` — connection, schema init, event log.
  `schema.sql` — tables. `import_data.py` — one-time seed. `seed/places.py` —
  name→lat/lon. `templates/` (Jinja + htmx), `static/` (vendored htmx + Leaflet).
- **The "current trip" is always the lowest-id `trip` row** (`SELECT * FROM trip
  ORDER BY id LIMIT 1`, app.py `load_person`). There is no trip switcher.
- **Every write appends one `event`** with a human-readable summary (the feed).
  Keep summaries in the code path, don't reconstruct from data.
- **A day's leg is derived by date**, not a FK: `start_date <= date < end_date`
  (`leg_for_date`). Pre-arrival and departure days have no leg on purpose.
- **Money:** each cost stores native `NZD`/`EUR`; roll-ups convert to EUR with
  the single `trip.fx_nzd_eur` (`to_eur`). No live FX.
- **htmx** returns small partials (`_idea_status.html`, `_task_item.html`) for
  inline swaps; everything else is plain forms + redirects.

## Adding or replacing a trip — read this before you touch it

**This app is single-trip by design (PLAN.md decision #2).** The `trip` table
holds one row as a hedge. Two facts make "just add another trip" break silently:

1. **No read query filters by `trip_id`.** Every list view (`SELECT * FROM leg
   ORDER BY seq`, `... FROM day`, `... FROM cost`, `... FROM event`, tasks,
   ideas) reads the whole table. `trip_id` is only ever *written*. A second trip
   row → both trips' legs/days/costs/ideas/events appear mixed in every view.
2. **`day.date` is globally `UNIQUE`** (schema.sql). Two trips can't hold the
   same calendar date, and day queries aren't trip-scoped anyway.

So there are two real paths, not one.

### Path A — Reuse the app for the next trip (the easy, supported one)

Use this when NZ 2027 is done (or shelved) and you want the same app for another
trip. It **replaces** the data; it does not run two trips at once.

1. **Back up first — the DB is the only copy of the plan.** On the NAS:
   `cp /volume1/docker/tripsite/data/trip.db /volume1/docker/tripsite/backup/trip-nz2027-archive.db`
   (and confirm it's in Dropbox via the nightly job). `import_data.py --wipe`
   destroys the current trip.
2. **Edit `import_data.py` constants** for the new trip: `TRIP` (name, dates,
   fx, budget), `LEGS`, `COSTS`, `TASKS`, `IDEAS`. Add any new destinations'
   coordinates to `seed/places.py` (no geocoding API — hand-set lat/lon).
3. **Reseed:** locally `python import_data.py --wipe --partner "Annick"`, or on
   the NAS `sudo docker exec tripsite python import_data.py --wipe --partner
   "Annick"`. The importer refuses to run without `--wipe` (guards against
   duplicate rows).
4. No code or container changes needed — the views are trip-agnostic because
   there's only ever one trip.

### Path B — True multi-trip (a real feature, not a config change)

Only if Wiljan wants NZ 2027 *and* another trip live at once. This is explicitly
out of scope in PLAN.md and is a genuine build. What it requires, at minimum:

- Scope **every** read query by the active `trip_id` (grep app.py for `FROM leg`,
  `FROM day`, `FROM idea`, `FROM cost`, `FROM task`, `FROM event` — none filter
  today).
- An "active trip" selector (a cookie like the person picker) + a trip switcher
  in `base.html`; `load_person` currently hardcodes the lowest-id trip.
- Schema change: `day.date UNIQUE` → `UNIQUE(trip_id, date)`, and generate days
  per trip; scope all day queries by trip.
- `import_data.py` without `--wipe` (append a trip), or a small "create trip" UX.
- Scope the feed, home stats, and costs roll-up by trip.

Don't half-build this. If asked, scope it as a feature with Wiljan, don't bolt a
second trip row onto the current single-trip queries.

## Working on it

- Local: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`,
  seed, then `./.venv/bin/python app.py` (http://127.0.0.1:5000). DB path is
  `TRIPSITE_DB` (defaults to `./data/trip.db`).
- Deploy is git-clone-on-NAS + `sudo docker compose up -d --build` (see
  `tech_setup/Tripsite-Setup.md`). NAS gotchas: Docker needs sudo; scp/SFTP is
  disabled (write files with `ssh 'cat > file'`); the compose build uses
  `network: host` to get past Synology's bridge-DNS failure during `pip install`.
