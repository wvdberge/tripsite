# Tripsite — implementation plan

> **Historical.** This is the original single-trip (NZ 2027) design. The app is
> now multi-trip (see `PLAN_MULTITRIP.md` for that build and `CLAUDE.md` for the
> current architecture). Decisions #2 (single-trip) and #9 (NZD-only money) below
> are superseded; the code lives at `personal/vakantie/tripsite/`, seeding is via
> `seed_trip.py` (no `import_data.py`, no `--wipe`).

Private, self-hosted trip-planning site for the NZ 2027 trip. Two users (Wiljan + partner), planning phase only. This plan is self-contained: execute it top to bottom without needing the design conversation that produced it.

## Why this exists

The trip currently lives in markdown files in this repo. That is single-player: the partner won't use git and dislikes markdown. The site gives both partners a friendly UI and async collaboration (one adds an idea Tuesday evening, the other sees it Wednesday). On-trip use (offline, "what are we doing today") is explicitly **out of scope** for v1.

## Locked decisions (do not relitigate)

1. **Source of truth:** the site's SQLite DB. The markdown files in `new_zealand_2027/` get a one-time import, after which they stop being the plan.
2. ~~**Scope:** NZ 2027 only. A `trip` table exists as a hedge (one row), but no trip-management UI, no trip switcher.~~ **Superseded:** the app is multi-trip; active trip is a `trip_id` cookie, `/trips` switches and creates trips.
3. **Stack:** Flask + SQLite + Jinja2 templates + htmx. Leaflet + OpenStreetMap tiles for the map (no API keys). No JS build step, no node_modules. Mobile-responsive (couch phone is a primary device).
4. **Hosting:** one Docker container on the Synology NAS, LAN-only. No internet exposure. Tailscale is the known future upgrade path; do not build for it now.
5. **Auth:** none. A name picker ("Who are you?") sets a cookie; that identity stamps authorship and feed events. No passwords.
6. **Days:** auto-generated for the trip date range. A day = its leg (derived from leg date ranges, not a FK) + pinned ideas + free-text note + energy marker (`rest`/`light`/`full`/unset). No time slots, no intra-day ordering.
7. **Tasks:** attached to a leg or an idea, plus one "general" list for orphans (e.g. packing). Strictly trip-scoped.
8. **Collaboration:** a "what's new" feed on the home page, driven by an `event` row appended on every write. No comments, no votes, no notifications.
9. **Money:** each cost line stores its native currency. Roll-ups display in EUR using a single editable trip-level rate. No live FX. *(Now per-trip: `trip.currency` + `trip.fx_to_eur`, e.g. NZD/0.56, GBP/1.1711 — was NZD-only.)*
10. **Language:** English UI. Data (place names, notes) is whatever users type.
11. **Backups:** nightly `sqlite3 .backup` on the NAS + an occasional copy committed into this repo (see Deployment).
12. **Process:** build the full MVP, then Wiljan shows his partner. No intermediate demo step.

## Repo layout

All code in `personal/vakantie/tripsite/`:

```
tripsite/
  PLAN.md            (this file)
  app.py             Flask app: routes + tiny helpers
  db.py              connection, schema init, event logging
  schema.sql
  import_data.py     one-time importer (idempotent: wipes and re-imports)
  seed/places.py     static dict: place name -> (lat, lon) for known stops
  templates/         Jinja2 (base, home, days, day_detail, legs, leg_detail,
                     ideas, idea_detail, costs, map, tasks, whoami)
  static/            style.css, htmx.min.js (vendored), leaflet vendored
  Dockerfile
  compose.yml        Portainer stack definition
  sync_db.sh         scp latest NAS backup into this repo
```

Vendor htmx and Leaflet into `static/` so the site works with no internet (LAN-only NAS).

## Schema

```sql
CREATE TABLE trip (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  start_date TEXT NOT NULL,          -- ISO dates throughout
  end_date TEXT NOT NULL,
  fx_nzd_eur REAL NOT NULL DEFAULT 0.56,
  budget_eur REAL                    -- overall target, nullable
);

CREATE TABLE person (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE leg (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  seq INTEGER NOT NULL,              -- order along the route
  name TEXT NOT NULL,                -- "Twizel (high country)"
  location TEXT,                     -- "Twizel, New Zealand"
  lat REAL, lon REAL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,            -- nights = end - start, computed in code
  accommodation TEXT,
  accommodation_status TEXT NOT NULL DEFAULT 'tbd'
    CHECK (accommodation_status IN ('tbd','shortlisted','booked')),
  confirmation_ref TEXT,
  notes TEXT
);

CREATE TABLE day (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  date TEXT NOT NULL UNIQUE,
  energy TEXT CHECK (energy IN ('rest','light','full')),  -- null = unset
  note TEXT
);

CREATE TABLE idea (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  title TEXT NOT NULL,
  location TEXT,
  lat REAL, lon REAL,
  url TEXT,
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'idea'
    CHECK (status IN ('idea','agreed','booked','rejected')),
  author_id INTEGER REFERENCES person(id),
  leg_id INTEGER REFERENCES leg(id),     -- optional "near this base"
  pinned_date TEXT,                      -- optional; pins the idea to a day
  created_at TEXT NOT NULL
);

CREATE TABLE cost (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  label TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('NZD','EUR')),
  kind TEXT NOT NULL CHECK (kind IN ('estimated','booked','actual')),
  category TEXT NOT NULL,               -- transport/accommodation/food/activities/other
  leg_id INTEGER REFERENCES leg(id),
  idea_id INTEGER REFERENCES idea(id)
);

CREATE TABLE task (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  title TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  leg_id INTEGER REFERENCES leg(id),
  idea_id INTEGER REFERENCES idea(id)   -- both null = general list
);

CREATE TABLE event (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  ts TEXT NOT NULL,
  person_id INTEGER REFERENCES person(id),
  summary TEXT NOT NULL                  -- "Wiljan pinned 'Milford cruise' to Feb 20"
);
```

Every write route appends one `event` with a human-readable summary. Keep summaries in the code path, not reconstructed from data.

## Routes / pages

| Route | Content |
|---|---|
| `GET /` | Home: what's-new feed (last ~20 events), trip countdown, quick stats (nights booked/total, budget booked vs estimate), open-task count |
| `GET /whoami` | Name picker; sets `person` cookie; every other page redirects here if the cookie is missing |
| `GET /days` | The calendar. All days grouped by leg, each row: date, energy badge, pinned ideas, note snippet. This is the flagship view |
| `GET/POST /days/<date>` | Day detail: edit note, set energy, pin/unpin ideas (htmx inline) |
| `GET /legs`, `GET/POST /legs/<id>` | Route overview and leg detail: dates, accommodation + status + confirmation ref, attached tasks, attached costs, nearby ideas |
| `GET /ideas` | Wishlist, filterable by status; add form at top (title + optional location/url/notes). Status changes inline via htmx |
| `GET/POST /ideas/<id>` | Idea detail: edit, attach to leg, pin to date, tasks, reject/agree/book |
| `GET /costs` | Roll-up in EUR by category and by kind (estimated/booked/actual) vs `budget_eur`; line list; add/edit; trip fx rate editable here |
| `GET /map` | Leaflet: numbered leg markers joined by a polyline + idea markers colored by status; popups link to detail pages |
| `GET /tasks` | Open tasks grouped: general first, then per leg/idea; checkbox toggles via htmx |

Editing model: plain forms + htmx swaps for inline bits (status, checkboxes, energy, pinning). No modal framework, no client state.

## One-time import (`import_data.py`)

Idempotent: `--wipe` drops and recreates all data, then imports. Sources are in `personal/vakantie/new_zealand_2027/`:

- **Trip row:** name "New Zealand 2027", `start_date` 2027-02-08 (AMS departure; Singapore stopover Feb 8–10 precedes the first NZ leg), `end_date` 2027-03-20, fx 0.56.
- **Persons:** Wiljan + partner. **Ask Wiljan for the partner's name before running the import** — it appears nowhere in the repo.
- **Legs:** parse `nz_route_mymaps.csv` (columns: Name, Location, Stop_Order, Dates, Nights, Type, Accommodation, Notes). Cross-check dates against the dated chain table in `itinerary_draft.md` — **the markdown table is authoritative where they disagree** (it is newer; the CSV may predate the Dunedin/Nelson revisions). Note the chain includes a "TBD — 2 nights parked" placeholder leg (Mar 13–15): import it as a real leg named "TBD (2 nights to reallocate)" with `accommodation_status='tbd'` — it must stay visible, not be silently dropped.
- **Booked accommodation** (set `accommodation_status='booked'` + refs, from `itinerary_draft.md` / `accommodation_strategy.md`):
  - Twizel: Mountain Chalets Motel, €122/nt × 4, free cancellation
  - Te Anau: TOP 10 studio, NZ$695/3nt, ref `#180797`
  - Punakaiki: Beach Camp family double, €111/2nt, Booking.com `#5738926961`
  - Abel Tasman: DOC Bark Bay tent site, NZ$154, ref `DOC #6414243`
- **Coordinates:** `seed/places.py` — hardcode approximate lat/lon for the ~17 stops and the well-known highlight locations (Milford Sound, Hooker Valley, Pancake Rocks, …). No geocoding API.
- **Costs** from `budget.md`, preserving kind and native currency. Minimum set: car SNAP ASX €1,815 booked (leg-less, category transport); fuel NZ$1,650 estimated; ferry NZ$400 estimated (transport); flights €5,427 estimated (not booked); TOP 10 membership NZ$55 booked-when-bought (check status); each booked accommodation above as a booked cost line attached to its leg; remaining accommodation as one estimated line (total accommodation estimate ~NZ$8,000 minus the booked lines); food NZ$3,000 estimated; activities NZ$4,000 estimated. Set `budget_eur` = 18000.
- **Tasks** from open `- [ ]` checkboxes in the markdown, attached where obvious. Minimum set: reserve child seat with SNAP (general/leg Christchurch), add second driver at desk, confirm one-way fee at desk, book Cook Strait ferry (leg Wellington; note the Interislander pricing options from `itinerary_draft.md`), book Abel Tasman water taxi (leg Abel Tasman; Aqua Taxi NZ$248 return), book flights, decide the TBD 2-night reallocation (leg TBD), discuss leave with employer.
- **Ideas** from the "Highlights by stop" section of `itinerary_draft.md`: one idea per highlight (status `idea`, author Wiljan, `leg_id` set, coordinates where known). Examples: Hooker Valley Track, Tekapo stargazing, Royal Albatross Centre, Penguin Place, Milford Sound cruise, glow-worm caves, Skyline Gondola + Luge, Puzzling World, Franz Josef glacier + Wildlife Centre, Pancake Rocks, Te Papa, Huka Falls. Hobbiton is scrapped (per itinerary) — do not import it.

After import, print a summary (counts per table) and leave the markdown files untouched.

## Deployment (Synology NAS, Portainer)

- `Dockerfile`: `python:3.12-slim`, install Flask + gunicorn, run `gunicorn -b 0.0.0.0:8000 app:app`.
- `compose.yml`: one service, port `8027:8000`, volume `/volume1/docker/tripsite/data:/data`, env `TRIPSITE_DB=/data/trip.db`. Deploy as a Portainer Stack (Wiljan is mid-migration to Portainer; this fits that pattern).
- DB file lives on the NAS volume. Claude Code reaches it over SSH when needed (`ssh nas sqlite3 ...`).
- **Backups:** Synology Task Scheduler, nightly:
  `sqlite3 /volume1/docker/tripsite/data/trip.db ".backup /volume1/docker/tripsite/backup/trip-$(date +%F).db"` — keep 30, and make sure the folder is inside the existing 3-2-1 backup scope. `sync_db.sh` scp's the latest backup into `new_zealand_2027/tripsite/` for occasional commit (read-only local copy for Claude).

Explain each Docker/SSH/cron command to Wiljan before running it (he's a CLI beginner and wants to understand what runs where).

## Build order and acceptance

Each phase ends runnable (`flask run` locally against a local `trip.db`; deploy to NAS at the end).

1. **Schema + import.** `import_data.py --wipe` produces a DB whose leg chain matches the 38-night table in `itinerary_draft.md` exactly (spot-check: Te Anau Feb 19–22 booked #180797; TBD leg present).
2. **Whoami + home + feed.** Name picker works; writes append events; home shows them.
3. **Days + legs.** `/days` shows all days Feb 8–Mar 20 grouped by leg (pre-arrival days show "travel/Singapore" gracefully, i.e. no leg). Energy + note editing inline.
4. **Ideas.** Add/edit/status-change/pin. Pinned ideas appear on their day.
5. **Costs.** EUR roll-up matches a hand check: booked lines alone ≈ €1,815 + €488 + €390 + €222 + €86 (± rounding at 0.56).
6. **Tasks.** Toggles work, grouped view correct.
7. **Map.** All legs numbered, polyline in seq order, ideas colored by status.
8. **Deploy to NAS + backup cron.** Reachable from a phone on home wifi.

Definition of done: partner can, from her phone on the couch with no instruction beyond the URL, pick her name, add an idea, and see it on the map and the feed.

## Out of scope (v1)

Offline/on-trip mode, comments, votes, notifications, multi-trip UI, drag-and-drop, user accounts/passwords, internet exposure, live FX rates, geocoding APIs.
