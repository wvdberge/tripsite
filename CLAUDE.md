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

## Adding a trip = build multi-trip support (do this, always)

**Standing decision from Wiljan: a new trip is added by extending the app to
hold multiple trips at once — never by wiping and replacing.** Every past trip
(NZ 2027, London, the UK cycle trip, whatever comes next) stays in the app.
Keeping that history is the whole point; do not throw it away to fit a new trip.

The app is single-trip *today* (PLAN.md decision #2): the `trip` table holds one
row and nothing scopes by it yet. So the first session that adds a second trip
builds proper multi-trip. Two facts make a naive "insert another trip row" break
silently — they are the work to do, not reasons to avoid it:

1. **No read query filters by `trip_id`.** Every list view (`SELECT * FROM leg
   ORDER BY seq`, `... FROM day`, `... FROM cost`, `... FROM event`, tasks,
   ideas) reads the whole table; `trip_id` is only ever *written*. Add a second
   trip and both trips' rows appear mixed in every view.
2. **`day.date` is globally `UNIQUE`** (schema.sql). Two trips can't hold the
   same calendar date, and day queries aren't trip-scoped anyway.

### What to build (scope it as a feature — don't half-build it)

- **Active-trip selector** — a cookie like the person picker, plus a trip
  switcher in `base.html`. `load_person` currently hardcodes the lowest-id trip
  (`SELECT * FROM trip ORDER BY id LIMIT 1`); replace that with the chosen trip.
- **Scope every read by the active `trip_id`** — grep app.py for `FROM leg`,
  `FROM day`, `FROM idea`, `FROM cost`, `FROM task`, `FROM event` (none filter
  today), plus the feed, home stats, and the costs roll-up.
- **Schema:** `day.date UNIQUE` → `UNIQUE(trip_id, date)`; generate days per
  trip; scope all day queries by trip. Migrate the existing NZ rows — back up the
  live DB and confirm the Dropbox copy first (see `tech_setup/Tripsite-Setup.md`).
- **Add-a-trip flow** — a "create trip" form (name, dates, fx, budget) that
  generates that trip's days, plus a per-trip way to seed legs/ideas.
  `import_data.py` currently hardcodes NZ constants and only runs with `--wipe`;
  generalise it (parameterise the dataset, drop the wipe) or add a UI path.

**Never run `import_data.py --wipe` to "add" a trip.** `--wipe` drops every
table; it is a dev/reset tool only and it destroys all trips at once.

## Working on it

- Local: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`,
  seed, then `./.venv/bin/python app.py` (http://127.0.0.1:5000). DB path is
  `TRIPSITE_DB` (defaults to `./data/trip.db`).
- Deploy is git-clone-on-NAS + `sudo docker compose up -d --build` (see
  `tech_setup/Tripsite-Setup.md`). NAS gotchas: Docker needs sudo; scp/SFTP is
  disabled (write files with `ssh 'cat > file'`); the compose build uses
  `network: host` to get past Synology's bridge-DNS failure during `pip install`.
