"""Migrate an existing tripsite DB from schema v2 to v3 (transport).

Run once per DB copy: ./.venv/bin/python migrate_v3.py  (honors TRIPSITE_DB).
Idempotent -- a second run no-ops. Safe to re-run.

v3 changes (see schema.sql):
  - new `transport` table (flights, ferries, trains, car rental, buses).
  - cost: add nullable `transport_id` so a cost can hang off a transport segment
    (in addition to the existing leg_id / idea_id).

Both changes are purely additive; no existing table is rebuilt or dropped, so
unlike migrate_v2 there is nothing to lose if it stops halfway. Foreign keys are
toggled off in autocommit mode around an explicit BEGIN/COMMIT for atomicity,
matching migrate_v2.
"""

import sqlite3
import sys

import db

TRANSPORT_DDL = """
CREATE TABLE transport (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL REFERENCES trip(id),
  leg_id INTEGER REFERENCES leg(id),
  kind TEXT NOT NULL DEFAULT 'flight'
    CHECK (kind IN ('flight','ferry','train','car','bus','other')),
  from_place TEXT,
  to_place TEXT,
  depart_date TEXT,
  depart_time TEXT,
  depart_tz TEXT,
  arrive_date TEXT,
  arrive_time TEXT,
  arrive_tz TEXT,
  provider TEXT,
  confirmation_ref TEXT,
  status TEXT NOT NULL DEFAULT 'booked'
    CHECK (status IN ('tbd','booked')),
  notes TEXT
)
"""


def counts(conn):
    tables = ("trip", "person", "leg", "day", "idea", "cost", "task", "event")
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables}


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def column_exists(conn, table, column):
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == column for c in cols)


def main():
    path = db.db_path()
    conn = sqlite3.connect(path)
    conn.isolation_level = None          # autocommit; we manage BEGIN/COMMIT

    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= 3:
        print(f"already migrated (user_version = {version}); nothing to do.")
        conn.close()
        return
    if version < 2:
        conn.close()
        sys.exit(f"DB is v{version}, expected v2. Run migrate_v2.py first.")

    before = counts(conn)

    conn.execute("PRAGMA foreign_keys = OFF")   # must be set outside a transaction
    conn.execute("BEGIN")
    try:
        if not table_exists(conn, "transport"):
            conn.execute(TRANSPORT_DDL)
        if not column_exists(conn, "cost", "transport_id"):
            conn.execute(
                "ALTER TABLE cost ADD COLUMN transport_id INTEGER REFERENCES transport(id)")
        conn.execute("PRAGMA user_version = 3")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    conn.execute("PRAGMA foreign_keys = ON")

    # --- post-migration integrity + row-count report ---
    fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    after = counts(conn)

    print(f"migrated {path} to user_version = 3")
    print("  added table 'transport' and column cost.transport_id")
    print("  row counts (before -> after):")
    for t in before:
        flag = "" if before[t] == after[t] else "  <-- CHANGED"
        print(f"    {t:8s} {before[t]:4d} -> {after[t]:4d}{flag}")
    if fk_problems:
        print("  FK CHECK FAILED:", fk_problems, file=sys.stderr)
        conn.close()
        sys.exit(1)
    print("  foreign_key_check: OK")
    conn.close()


if __name__ == "__main__":
    main()
