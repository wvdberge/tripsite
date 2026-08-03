-- Tripsite schema. SQLite. ISO date strings (YYYY-MM-DD) throughout.
-- Multi-trip: many trip rows, everything scoped by trip_id. The active trip is
-- a cookie (app.py load_person). People are global (shared across all trips).

CREATE TABLE trip (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'EUR',   -- the trip's local currency code
  fx_to_eur REAL NOT NULL DEFAULT 1.0,    -- EUR per 1 unit of that currency
  budget_eur REAL
);

CREATE TABLE person (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE leg (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  seq INTEGER NOT NULL,
  name TEXT NOT NULL,
  location TEXT,
  lat REAL, lon REAL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  accommodation TEXT,
  accommodation_status TEXT NOT NULL DEFAULT 'tbd'
    CHECK (accommodation_status IN ('tbd','shortlisted','booked')),
  confirmation_ref TEXT,
  notes TEXT
);

CREATE TABLE day (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  date TEXT NOT NULL,
  energy TEXT CHECK (energy IN ('rest','light','full')),
  note TEXT,
  UNIQUE(trip_id, date)
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
  leg_id INTEGER REFERENCES leg(id),
  pinned_date TEXT,
  created_at TEXT NOT NULL
);

-- Transport segments: flights, ferries, trains, car rental, buses. Trip-scoped;
-- leg_id is usually NULL and set only when a segment clearly belongs to one stay
-- (e.g. a water taxi across the Tasman). Times are optional 'HH:MM' text; the
-- zone is a short label shown verbatim ('CET', 'NZDT') -- the app derives nothing
-- from it (no DST maths, no elapsed time). Ordered by depart_date, depart_time.
CREATE TABLE transport (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  leg_id INTEGER REFERENCES leg(id),
  kind TEXT NOT NULL DEFAULT 'flight'
    CHECK (kind IN ('flight','ferry','train','car','bus','other')),
  from_place TEXT,
  to_place TEXT,
  depart_date TEXT,          -- YYYY-MM-DD
  depart_time TEXT,          -- 'HH:MM', nullable
  depart_tz TEXT,            -- short zone label shown verbatim, nullable
  arrive_date TEXT,          -- nullable
  arrive_time TEXT,
  arrive_tz TEXT,
  provider TEXT,
  confirmation_ref TEXT,
  status TEXT NOT NULL DEFAULT 'booked'
    CHECK (status IN ('tbd','booked')),
  notes TEXT
);

CREATE TABLE cost (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  label TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL,   -- 'EUR' or the trip's local currency; validated in the app
  kind TEXT NOT NULL CHECK (kind IN ('estimated','booked','actual')),
  category TEXT NOT NULL,
  leg_id INTEGER REFERENCES leg(id),
  idea_id INTEGER REFERENCES idea(id),
  transport_id INTEGER REFERENCES transport(id)  -- a cost hangs off a leg, idea, OR transport
);

CREATE TABLE task (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  title TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  leg_id INTEGER REFERENCES leg(id),
  idea_id INTEGER REFERENCES idea(id)
);

CREATE TABLE event (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  ts TEXT NOT NULL,
  person_id INTEGER REFERENCES person(id),
  summary TEXT NOT NULL
);

PRAGMA user_version = 3;
