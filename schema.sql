-- Tripsite schema. SQLite. ISO date strings (YYYY-MM-DD) throughout.
-- Single trip (NZ 2027); the trip table is a one-row hedge, no trip-management UI.

CREATE TABLE trip (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  fx_nzd_eur REAL NOT NULL DEFAULT 0.56,
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
  date TEXT NOT NULL UNIQUE,
  energy TEXT CHECK (energy IN ('rest','light','full')),
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
  leg_id INTEGER REFERENCES leg(id),
  pinned_date TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE cost (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  label TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('NZD','EUR')),
  kind TEXT NOT NULL CHECK (kind IN ('estimated','booked','actual')),
  category TEXT NOT NULL,
  leg_id INTEGER REFERENCES leg(id),
  idea_id INTEGER REFERENCES idea(id)
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
