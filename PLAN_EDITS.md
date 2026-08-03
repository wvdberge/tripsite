# Plan: more in-app editing for tripsite

Goal: make the app editable where it is currently read-only, so the website (not
hand-written scripts) becomes the way you change things. Five features, agreed
after grilling. Nothing here wipes data; the DB stays the source of truth.

## Scope, decided

1. **Edit and delete tasks** — change a task's text inline, or delete it.
2. **Transport as a real thing** — a new `transport` table (flights, ferries,
   trains, car rental, buses), with its own page and form.
3. **Add and edit stays (legs)** — add a new stay through the site, and edit a
   stay's name, place, and dates (not just the hotel field). Guarded delete.
4. **Edit the whole trip** — name, dates, budget, currency, exchange rate.
5. **Costed day trips + editable costs** — wire the existing (unused) cost↔idea
   link into the screens so an idea can carry a cost and become a "day trip";
   also let you edit and attach a cost line, not just add/delete it.

Explicitly out of scope: geocoding (no coordinate lookup; you paste coords or get
no map pin), timezone maths (zone is a label only), reassigning a task between
stays/ideas (delete + re-add in the rare case).

---

## Database changes (one migration, additive only)

Two additions, both safe (nothing existing is touched or dropped):

- **New `transport` table:**

  ```sql
  CREATE TABLE transport (
    id INTEGER PRIMARY KEY,
    trip_id INTEGER NOT NULL REFERENCES trip(id),
    leg_id  INTEGER REFERENCES leg(id),      -- usually NULL; set only when a
                                             -- segment clearly belongs to one stay
                                             -- (e.g. a water taxi across the Tasman)
    kind TEXT NOT NULL DEFAULT 'flight'
      CHECK (kind IN ('flight','ferry','train','car','bus','other')),
    from_place TEXT,
    to_place   TEXT,
    depart_date TEXT,                        -- YYYY-MM-DD
    depart_time TEXT,                        -- 'HH:MM', nullable
    depart_tz   TEXT,                        -- short zone label shown verbatim, e.g. 'CET' (nullable)
    arrive_date TEXT,                        -- nullable
    arrive_time TEXT,
    arrive_tz   TEXT,
    provider TEXT,                           -- 'Cathay Pacific', 'Interislander'…
    confirmation_ref TEXT,
    status TEXT NOT NULL DEFAULT 'booked'
      CHECK (status IN ('tbd','booked')),
    notes TEXT
  );
  ```

  Ordered by `depart_date`, then `depart_time`. For the car rental, from/to =
  pickup/dropoff and the two datetimes = pickup/dropoff, which reads fine.
  Timezone is a **short label you type or pick** (e.g. "CET", "NZDT", "HKT"),
  shown back exactly as entered. Display reads "10 Feb 21:55 CET → 12 Feb 12:50
  NZDT". The app derives nothing from it (no abbreviation lookup, no DST maths, no
  elapsed time) — that keeps zone logic out entirely, which is the point of
  "label only". Times and zones are optional.

- **New column `cost.transport_id`** (`ALTER TABLE cost ADD COLUMN transport_id
  INTEGER REFERENCES transport(id)`). This is what lets a flight's price live in
  the one money model instead of being duplicated. A cost line can now point at a
  stay, an idea, **or** a transport segment. The costs roll-up already sums by
  trip, so a transport cost lands in the totals with no extra work.

- Bump `PRAGMA user_version = 3` in `schema.sql`, and mirror both additions there
  so a fresh install gets them. (Verified safe: `schema.sql` uses plain
  `CREATE TABLE`, but `init_schema` runs only from `seed_trip.py` on a fresh DB,
  never on normal app boot, so editing `schema.sql` can't break the live v2 DB.)

- **`migrate_v3.py`** — a new idempotent script mirroring `migrate_v2.py`:
  checks `user_version`, creates the table + column if missing, sets version to 3,
  no-ops on a second run. Run it once against each DB copy (local and the live
  NAS DB via `TRIPSITE_DB=/data/trip.db`), after a backup. See
  `tech_setup/Tripsite-Setup.md` and the live-DB-edit note in memory.

The "day trip" feature needs **no** schema change: `cost.idea_id` already exists,
it was just never exposed in the forms.

---

## Feature 1 — edit and delete tasks

Tasks already render as small htmx rows (`_task_item.html`) with an inline toggle.
Edit and delete follow the same pattern, no new page.

- **`app.py`:** two routes.
  - `POST /tasks/<id>/edit` — update `title`, log an event, return the swapped
    `_task_item.html` partial.
  - `POST /tasks/<id>/delete` — delete, log an event, htmx-remove the row.
- **`_task_item.html`:** add a small "edit" affordance (click the text → it
  becomes an input → submit swaps the row back) and a delete "✕". Keep the row as
  the single source of truth for a task's markup.

## Feature 2 — transport

- **`app.py`:** routes mirroring the ideas/costs shape.
  - `GET /transport` — chronological list for the active trip, grouped by kind or
    flat, each row showing kind, from→to, dates/times with zone labels, provider,
    ref, status, and its attached cost if any.
  - `POST /transport/add` — create a segment.
  - `GET/POST /transport/<id>` — detail + edit (all fields), and an "add cost"
    box here (attaches a cost with `transport_id` set), the same way ideas will
    get costs.
  - `POST /transport/<id>/delete` — inside one transaction, delete its attached
    cost lines first (by `transport_id`), then the segment. Confirm popup, same
    approach as stays below. (Foreign keys are ON with no `ON DELETE CASCADE`, so
    every delete must remove children by hand or SQLite raises `IntegrityError`.)
- **Templates:** new `transport.html` (list) and `transport_detail.html` (or one
  page with an inline edit form, matching `leg_detail.html`). A short dropdown of
  zone labels (Europe/Amsterdam, Asia/Hong_Kong, Pacific/Auckland, Europe/London,
  plus a free "other").
- **`day_detail.html`:** surface transport whose `depart_date` or `arrive_date`
  is that day, next to the pinned ideas, e.g. "✈ Flight to CHC departs 21:55".
  One extra query in the `day_detail` route.
- **`base.html`:** add "Transport" to the nav.

## Feature 3 — add and edit stays (legs)

- **`app.py`:**
  - `POST /legs/add` — create a stay from name, place, start/end dates, optional
    coordinates, and the accommodation fields. **Auto-order:** after insert,
    renumber every leg's `seq` by `start_date` so you never type a sequence number.
    Editing a stay's dates re-runs the same renumber.
  - Extend the existing `POST /legs/<id>` edit to also accept `name`, `location`,
    `start_date`, `end_date`, `lat`, `lon` (today it only takes the accommodation
    fields).
  - `POST /legs/<id>/delete` — delete the stay **and everything attached**, behind
    a confirm popup that says exactly that. Foreign keys are ON and the schema has
    no `ON DELETE CASCADE`, so SQLite won't cascade for us; the route deletes
    children by hand, in dependency order, in **one transaction**:
    1. For each idea on the stay: delete that idea's costs and tasks (by `idea_id`).
    2. Delete the stay's own costs, tasks, and ideas (by `leg_id`).
    3. Delete transport pointing at the stay, and its costs (by `leg_id` →
       `transport_id`).
    4. Delete the stay.
    The popup text must list all of it (costs, tasks, ideas, **and any transport**
    tied to the stay), since Feature 2 adds `transport.leg_id`.
- **Templates:** an add-stay form on `legs.html`; open the extra fields on
  `leg_detail.html`; a JS `confirm()` on the delete button. Optional lat/lon is a
  plain text pair ("paste from Google Maps"); blank = no map pin, stay still works.

## Feature 4 — edit the whole trip

- **`app.py`:** `POST /trips/<id>/edit` — update name, start_date, end_date,
  budget, currency, fx_to_eur. When start/end change, **resync the day rows** the
  way `create_trip` and `update_flights_nz.py` already do: add missing dates,
  delete out-of-range ones. Log an event.
- **Caveat to surface in the UI:** trimming the date range deletes those days'
  notes and energy marks, can leave a stay sitting outside the trip's dates (it
  survives, just without day pages), and can leave an idea pinned to a date that no
  longer exists (`idea.pinned_date` is free text, not a foreign key, so it
  dangles). On resync, clear `pinned_date` for any idea pinned to a removed date.
  The edit form warns before saving.
- **Templates:** an edit form on `trips.html` (or a small `/trips/<id>/edit`
  page), pre-filled.

## Feature 5 — costed day trips + editable costs

- **Cost editing:** `POST /costs/<id>/edit` — edit label, amount, currency, kind,
  category, and what it's attached to. Inline on `costs.html`, matching the
  existing add/delete forms.
- **One "attach to" picker:** the cost add/edit form gets a single picker to hang
  the cost off a stay, an idea, or a transport segment (mutually exclusive). Today
  it only offers a stay. Enforce "at most one of leg/idea/transport" **in the
  route**, not just in the picker markup, so a hand-posted form can't set two.
- **Ideas carry costs:** `idea_detail` route also fetches the idea's costs and
  shows them, with an "add cost" box on the page. An idea that is pinned to a date
  and has a cost is a "day trip" — no separate concept, and it already appears on
  that day's page because pinned ideas do.

---

## Files touched

- `schema.sql` — transport table, `cost.transport_id`, `user_version = 3`.
- `migrate_v3.py` — **new**, idempotent live-DB migration.
- `app.py` — new routes for tasks (edit/delete), transport (CRUD), legs
  (add/fuller edit/delete), trips (edit), costs (edit + attach picker), idea
  costs; day_detail transport surfacing.
- `templates/` — new `transport.html` (+ detail); edits to `_task_item.html`,
  `legs.html`, `leg_detail.html`, `trips.html`, `costs.html`, `idea_detail.html`,
  `day_detail.html`, `base.html` (nav).
- `CLAUDE.md` — document the transport model and the widened edit surface; note
  the v3 migration.

## Order of work

1. Migration first (`schema.sql` + `migrate_v3.py`), run on the local DB, confirm
   the app still boots.
2. Feature 1 (tasks) — smallest, proves the inline-edit pattern.
3. Feature 5 (costs edit + attach + idea costs) — reuses existing money model.
4. Feature 3 (legs add/edit/delete).
5. Feature 4 (trip edit).
6. Feature 2 (transport) — largest; new page, form, day surfacing.
7. Update `CLAUDE.md`. Test locally end-to-end.
8. Back up the live NAS DB, run `migrate_v3.py` against it, deploy, smoke-test.

## Deploy / live-DB note

The live DB on the NAS is the source of truth. The schema change reaches it by
running `migrate_v3.py` **inside the container** against `/data/trip.db`, after a
backup, not by pushing a code file over the DB. Ordinary content edits still
follow the pull-edit-push-whole-file rule (app idle) from memory
`project_tripsite_live_db_edits`. Deploy the new code the usual way
(git-clone-on-NAS + `sudo docker compose up -d --build`, per
`tech_setup/Tripsite-Setup.md`).
