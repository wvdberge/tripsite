# PLAN_MULTITRIP.md — generalize tripsite to hold multiple trips

Execution plan for a future Claude session (Opus or Sonnet). Read `CLAUDE.md`
first; its "Adding a trip = build multi-trip support" section records the
standing decisions this plan implements. Work through the phases in order.
Each phase ends with a verification step; do not continue past a failed one.

## Goal

1. Move this repo from `~/personal/vakantie/new_zealand_2027/tripsite/` to
   `~/personal/vakantie/tripsite/` (it serves all trips now, not just NZ).
2. Make the app hold multiple trips at once, with a trip switcher and a
   create-trip flow. Never wipe existing data.
3. Seed the UK cycling trip (Hadrian's Cycleway, Aug 20 – Sep 4, 2026) as the
   second trip, from `~/personal/vakantie/uk_cycling/itinerary.md` and
   `costs.md`.

## Locked decisions (do not relitigate)

- **Additive only.** The NZ 2027 data in the live DB survives untouched.
  `import_data.py --wipe` is never part of adding a trip.
- **New repo location:** `~/personal/vakantie/tripsite/`.
- **Per-trip currency.** `trip.fx_nzd_eur` becomes `trip.currency` (the trip's
  local currency code) plus `trip.fx_to_eur` (EUR per 1 unit of that
  currency). Costs store either EUR or the trip's local currency. NZ keeps
  NZD/0.56; UK gets GBP/1.1711.
- **Active trip = cookie**, same pattern as the person cookie. A `/trips`
  page lists trips, switches the active one, and holds the create-trip form.
- **People stay global** (Wiljan + Annick apply to every trip). No change to
  the `person` table.
- **Schema versioning** via `PRAGMA user_version` (currently 0; this work
  sets it to 2). Migration is a standalone script, run once per DB copy.

---

## Phase 0 — Backups (do this before touching anything)

1. Read `~/personal/tech_setup/Tripsite-Setup.md` for the deploy/backup
   details (NAS host, container name, DB path, sync_db.sh usage).
2. Pull a fresh copy of the live NAS DB with `./sync_db.sh` (or the manual
   `ssh 'cat …'` route the setup doc describes; scp is disabled on the NAS).
3. Copy the live DB twice: once as the local working DB
   (`./data/trip.db`), once as a dated backup
   (`./data/trip.db.pre-multitrip-YYYYMMDD.bak`). Verify the backup opens:
   `sqlite3 <backup> 'SELECT COUNT(*) FROM day'` (expect 41).
4. Confirm the Dropbox backup copy mentioned in Tripsite-Setup.md exists and
   is recent. If it is missing or stale, stop and tell Wiljan.

## Phase 1 — Move the repo

The tripsite is its own git repo (`git@github.com:wvdberge/tripsite.git`)
nested inside the `personal` repo and gitignored there
(`personal/.gitignore` line: `vakantie/new_zealand_2027/tripsite/`).

1. `mv ~/personal/vakantie/new_zealand_2027/tripsite ~/personal/vakantie/tripsite`
   (a plain move; the `.git` dir moves with it, nothing to re-clone).
2. In `~/personal/.gitignore`, change the ignore line to `vakantie/tripsite/`.
3. Update every doc that states the old path:
   - `~/personal/tech_setup/Tripsite-Setup.md`
   - `~/personal/vakantie/CLAUDE.md` (also: its trip table says Hexham and
     Newcastle accommodation are TBD; `uk_cycling/costs.md` says all UK
     accommodation is booked — fix the status while there)
   - `tripsite/CLAUDE.md` (the header references `../` for NZ markdown
     sources; those now live at `../new_zealand_2027/`)
4. The NAS deploy clones from GitHub, so nothing changes on the NAS.
5. Verify: `cd ~/personal/vakantie/tripsite && git status` is clean and
   `git remote -v` still shows `wvdberge/tripsite`. The app still runs
   locally (Phase 2's venv note).

## Phase 2 — Schema v2 + migration script

Local dev setup (Python is not Wiljan's language; keep this exact):
`python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`,
run with `./.venv/bin/python app.py`, DB path env var `TRIPSITE_DB`
(defaults to `./data/trip.db`).

### schema.sql changes (for fresh DBs)

- `trip`: replace `fx_nzd_eur REAL NOT NULL DEFAULT 0.56` with
  `currency TEXT NOT NULL DEFAULT 'EUR'` and
  `fx_to_eur REAL NOT NULL DEFAULT 1.0`.
- `day`: change `date TEXT NOT NULL UNIQUE` to `date TEXT NOT NULL` plus a
  table constraint `UNIQUE(trip_id, date)`.
- `cost`: drop the `CHECK (currency IN ('NZD','EUR'))`; keep
  `currency TEXT NOT NULL`. The app validates currency against
  `{'EUR', trip.currency}` instead.
- End the file with `PRAGMA user_version = 2;`.

### migrate_v2.py (new file, for existing DBs)

A standalone script: `./.venv/bin/python migrate_v2.py` (honors
`TRIPSITE_DB`). Behavior:

1. If `PRAGMA user_version` >= 2, print "already migrated" and exit 0
   (idempotent; safe to re-run).
2. Inside one transaction, with `PRAGMA foreign_keys = OFF` for the rebuild:
   - `trip`: `ALTER TABLE trip RENAME COLUMN fx_nzd_eur TO fx_to_eur;`
     then `ALTER TABLE trip ADD COLUMN currency TEXT NOT NULL DEFAULT 'EUR';`
     then `UPDATE trip SET currency = 'NZD';` (every existing row is the NZ
     trip).
   - `day`: SQLite cannot drop a column-level UNIQUE, so rebuild: create
     `day_new` with the v2 definition, `INSERT INTO day_new SELECT * FROM
     day`, drop `day`, rename `day_new` to `day`.
   - `cost`: rebuild the same way to drop the currency CHECK (create
     `cost_new` per v2, copy all rows, drop, rename).
   - `PRAGMA user_version = 2;`
3. After commit, run `PRAGMA foreign_key_check` and print row counts per
   table so the output is comparable to a pre-migration count.

### Verify

On a scratch copy of the live DB: run the migration twice (second run must
no-op), then check row counts match pre-migration, `SELECT currency,
fx_to_eur FROM trip` returns `NZD, 0.56`, and inserting two `day` rows with
the same date but different `trip_id` succeeds while a same-trip duplicate
date fails.

## Phase 3 — App: active trip, scoped queries, switcher, create-trip

### 3a. Active-trip resolution (`app.py: load_person`)

Replace `SELECT * FROM trip ORDER BY id LIMIT 1` with:

1. Read cookie `trip_id`; if it matches a trip row, use it.
2. Otherwise pick a default: among trips with `end_date >= today`, the one
   with the earliest `start_date`; if none, the trip with the latest
   `end_date`. (So the next upcoming trip wins; after all trips pass, the
   most recent one shows.)
3. If the trip table is empty, redirect everything except `/trips`, `/whoami`
   and static to `/trips` so a fresh install lands on the create form.

### 3b. Scope every read by `g.trip["id"]`

Grep `app.py` for `FROM leg`, `FROM day`, `FROM idea`, `FROM cost`,
`FROM task`, `FROM event`. Every query that does not already filter by a
row id must gain `trip_id = ?`. The full list as of now (line numbers
approximate):

- `leg_for_date` helper — add `AND trip_id = ?`.
- `inject_globals` — open-task count.
- `home` — events feed, legs list, costs, open-task count.
- `days` — day list, pinned-ideas query.
- `day_detail` — the day lookup and both UPDATEs key on `date` alone;
  they must key on `(trip_id, date)` now that dates repeat across trips.
  Also the pinned and candidates queries.
- `legs` — leg list.
- `ideas` — the list query.
- `idea_detail` — `legs_all`, `days_all` dropdowns.
- `costs` — cost rows, `legs_all` dropdown.
- `tasks` — task rows, legs dropdown.
- `trip_map` — legs and ideas queries.

Routes that fetch by primary key (`leg_detail`, `idea_detail`, `pin/unpin`,
`toggle_task`, `delete_cost`): add `AND trip_id = ?` to the lookup so a
stale URL from another trip 404s instead of editing the wrong trip's row.

Remove `db.trip_id()` (its docstring says "the app is single-trip by
design"; nothing should use it after this phase).

### 3c. Currency helper

`to_eur(amount, currency)`: EUR passes through; anything else multiplies by
`g.trip["fx_to_eur"]`. Validate cost-form currency against
`{'EUR', g.trip['currency']}` in `add_cost`.

### 3d. Templates

- `base.html`: the brand hardcodes `🇳🇿`. Make the trip name link to
  `/trips` (or add a small "Trips" nav link) so switching is reachable from
  everywhere. Simplest: drop the flag emoji; optionally add a nullable
  `trip.emoji` column in the v2 schema/migration if a per-trip emoji is
  wanted (nice, not required).
- `costs.html`: replace hardcoded "NZD" (three spots: the roll-up caption,
  the currency `<select>`, the FX form label) with `trip.currency`, and
  `trip.fx_nzd_eur` with `trip.fx_to_eur`. When `trip.currency == 'EUR'`,
  hide the FX form and show a single-currency select.
- `map.html` already fits bounds to markers, so it recenters per trip;
  only the empty-map fallback `setView([-42, 172], 5)` is NZ-centric.
  Acceptable; change only if trivial.
- `home.html`: countdown goes negative once a trip starts. Show "underway"
  during the trip and "done" after, instead of a negative number.

### 3e. `/trips` page (new route + template)

- List all trips (name, dates, currency, a "booked X of Y nights" line),
  mark the active one, and switch on click (set the `trip_id` cookie,
  redirect home, log a feed event "X switched to trip Y" — scoped to the
  target trip).
- Create-trip form: name, start date, end date, currency code, fx_to_eur,
  budget_eur. On submit: insert the trip, generate one `day` row per date
  from start through end inclusive, log a feed event, set the new trip
  active, redirect home. Legs/ideas/costs/tasks start empty; they are added
  through the existing UI or a seed module (Phase 4).

### Verify (local, on the migrated copy of the live DB)

Run the app, click through every page as both people. The NZ trip must look
exactly as before the change (same legs, days, ideas, costs totals, tasks,
feed). Create a throwaway trip via the form, switch to it, confirm every
page shows it empty and the NZ pages are unchanged, switch back, then
delete the throwaway rows from the DB (or re-copy the backup and re-migrate).

## Phase 4 — Seed refactor + UK trip data

### 4a. Restructure the seeder

- Move the NZ constants (`TRIP`, `LEGS`, `COSTS`, `TASKS`, `IDEAS`) out of
  `import_data.py` into `seed/trips/nz2027.py`. The trip dict gains
  `"currency": "NZD"` and renames `fx` to `fx_to_eur`.
- New CLI `seed_trip.py <module>` (e.g. `seed_trip.py uk2026`): imports
  `seed/trips/<module>.py`, refuses if a trip with that name already exists,
  inserts trip + legs + days + costs + tasks + ideas additively, creates
  missing people but never duplicates them, logs one import feed event, no
  wipe anywhere. Reuse `import_data.py`'s insert logic.
- Delete `import_data.py` and drop `db.wipe()`, or keep them only behind an
  explicit `--dev-reset` flag with a loud warning. Deleting is cleaner; the
  NZ data now lives in `seed/trips/nz2027.py` for a from-scratch rebuild.

### 4b. `seed/trips/uk2026.py`

Transcribe from `~/personal/vakantie/uk_cycling/itinerary.md` (schedule,
day details) and `costs.md` (amounts, booked status). Those files are
authoritative; re-read them at execution time rather than trusting this
summary. Outline:

- **Trip:** name "UK Cycling 2026 — Hadrian's Cycleway", 2026-08-20 to
  2026-09-04, currency GBP, fx_to_eur 1.1711, budget_eur 3365.
- **Legs** (all accommodation booked; where you sleep each night):
  1. DFDS ferry outbound (IJmuiden → Newcastle), Aug 20–21
  2. Newcastle (arrival) — Premier Inn Millennium Bridge, Aug 21–22
  3. Carlisle — Brooklyn House, Aug 22–24
  4. Brampton — Scotch Arms Mews, Aug 24–26
  5. Haltwhistle — Hillis Close Farm Cottage, Aug 26–28
  6. Hexham — Abbey Apartment, Aug 28–31
  7. Newcastle (end) — Caledonian Hotel, Jesmond, Aug 31 – Sep 3
  8. DFDS ferry return (Newcastle → IJmuiden), Sep 3–4
  Put route/terrain notes from itinerary.md in each leg's `notes` (e.g.
  Haltwhistle → Hexham is the hilly Military Road section; the 3-night
  Hexham stay is a deliberate recovery buffer; Thule converts to stroller
  mode for the train and the ferry).
- **Coords** for `seed/places.py` (approximate; eyeball them on the map
  page after seeding): Newcastle 54.9738, −1.6132; Carlisle 54.8925,
  −2.9329; Brampton 54.944, −2.734; Haltwhistle 54.970, −2.457; Hexham
  54.971, −2.101; North Shields ferry terminal 55.008, −1.440; IJmuiden
  52.460, 4.610.
- **Costs** (per costs.md): ferry €698 booked (transport, trip-level);
  per-leg booked accommodation €78 / €242 / €323 / €277 / €440 / €347
  (store the two GBP-native ones as GBP £67 and £276 if you want native
  amounts, or keep costs.md's EUR figures; either is fine, note the choice
  in the label); trains/misc €100 estimated; food & activities €860
  estimated.
- **Tasks:** confirm DFDS balance was paid (was due Jul 21, 2026); book
  the Newcastle → Carlisle train (Aug 22, bikes + Thule in stroller mode);
  anything unchecked in the uk_cycling markdown.
- **Ideas** (from itinerary.md, attach to legs): Solway Coast loop to
  Bowness-on-Solway; Lanercost Priory; Talkin Tarn; South Tyne loop /
  Lambley Viaduct; Roman Army Museum; Vindolanda; Housesteads; Hexham
  Abbey; Corbridge loop; Dilston Physic Garden; Discovery Museum; Great
  North Museum; Tynemouth beach.

### Verify

Seed locally, then click through every page on the UK trip: 8 legs, 16
days, costs roll-up ≈ €3,365 total with €2,405 booked (698 + 1,707), map
markers along the Tyne–Solway corridor, NZ trip still intact. Run
`seed_trip.py uk2026` a second time; it must refuse.

## Phase 5 — Docs, deploy, migrate the live DB

1. Update `tripsite/CLAUDE.md`: the app is now multi-trip; replace the
   whole "Adding a trip = build multi-trip support" section with a short
   "adding a trip = write a seed module + `seed_trip.py <name>`, never
   wipe" note; document the trip cookie and `/trips`; update the currency
   description; note the new repo location. Update `README.md` and
   `PLAN.md`'s locked-decision list similarly. Add the UK trip to
   `vakantie/CLAUDE.md`'s tripsite mentions if any.
2. Commit and push (`wvdberge/tripsite`). Sensible split: repo-move docs /
   schema+migration / app scoping+switcher / seeds / docs.
3. Deploy per `tech_setup/Tripsite-Setup.md` (git pull on the NAS, `sudo
   docker compose up -d --build`; the compose build needs `network: host`
   for pip).
4. On the NAS, back up the live DB again, then run `migrate_v2.py` and
   `seed_trip.py uk2026` against it (inside the container with
   `TRIPSITE_DB=/data/trip.db`, or however Tripsite-Setup.md prescribes).
5. Verify on `http://192.168.1.202:8027` from a phone: both trips present,
   switcher works, NZ untouched, UK complete.
6. Update Wiljan's memory/docs that say the tripsite is "the NZ 2027 trip
   planner" to "the family trip planner (NZ 2027 + UK 2026 + future
   trips)".

## Out of scope (do not build)

- Live FX rates, authentication, trip archiving/deletion UI, per-trip
  people, editing legs through the UI beyond what exists today. Add nothing
  the phases above do not name.
