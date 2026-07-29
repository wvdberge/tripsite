"""Migrate an existing tripsite DB from schema v1 (single-trip) to v2 (multi-trip).

Run once per DB copy: ./.venv/bin/python migrate_v2.py  (honors TRIPSITE_DB).
Idempotent — a second run no-ops. Safe to re-run.

v2 changes (see schema.sql):
  - trip.fx_nzd_eur -> fx_to_eur, plus a new trip.currency (set to 'NZD' for the
    one existing NZ trip).
  - day: drop the global UNIQUE on date, add UNIQUE(trip_id, date).
  - cost: drop the CHECK (currency IN ('NZD','EUR')); the app validates instead.

SQLite ignores `PRAGMA foreign_keys` while a transaction is open, so the pragma
is toggled in autocommit mode (isolation_level = None) around an explicit
BEGIN/COMMIT. That also gives real atomicity: an interrupted run rolls back whole.
"""

import sqlite3
import sys

import db


def counts(conn):
    tables = ("trip", "person", "leg", "day", "idea", "cost", "task", "event")
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables}


def main():
    path = db.db_path()
    conn = sqlite3.connect(path)
    conn.isolation_level = None          # autocommit; we manage BEGIN/COMMIT

    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= 2:
        print(f"already migrated (user_version = {version}); nothing to do.")
        conn.close()
        return

    before = counts(conn)

    conn.execute("PRAGMA foreign_keys = OFF")   # must be set outside a transaction
    conn.execute("BEGIN")
    try:
        # --- trip: rename fx column, add currency, tag the existing NZ trip ---
        conn.execute("ALTER TABLE trip RENAME COLUMN fx_nzd_eur TO fx_to_eur")
        conn.execute("ALTER TABLE trip ADD COLUMN currency TEXT NOT NULL DEFAULT 'EUR'")
        conn.execute("UPDATE trip SET currency = 'NZD'")

        # --- day: rebuild to swap UNIQUE(date) for UNIQUE(trip_id, date) ---
        conn.execute(
            "CREATE TABLE day_new ("
            "  id INTEGER PRIMARY KEY,"
            "  trip_id INTEGER NOT NULL REFERENCES trip(id),"
            "  date TEXT NOT NULL,"
            "  energy TEXT CHECK (energy IN ('rest','light','full')),"
            "  note TEXT,"
            "  UNIQUE(trip_id, date)"
            ")")
        conn.execute("INSERT INTO day_new SELECT * FROM day")
        conn.execute("DROP TABLE day")
        conn.execute("ALTER TABLE day_new RENAME TO day")

        # --- cost: rebuild to drop the currency CHECK constraint ---
        conn.execute(
            "CREATE TABLE cost_new ("
            "  id INTEGER PRIMARY KEY,"
            "  trip_id INTEGER NOT NULL REFERENCES trip(id),"
            "  label TEXT NOT NULL,"
            "  amount REAL NOT NULL,"
            "  currency TEXT NOT NULL,"
            "  kind TEXT NOT NULL CHECK (kind IN ('estimated','booked','actual')),"
            "  category TEXT NOT NULL,"
            "  leg_id INTEGER REFERENCES leg(id),"
            "  idea_id INTEGER REFERENCES idea(id)"
            ")")
        conn.execute("INSERT INTO cost_new SELECT * FROM cost")
        conn.execute("DROP TABLE cost")
        conn.execute("ALTER TABLE cost_new RENAME TO cost")

        conn.execute("PRAGMA user_version = 2")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    conn.execute("PRAGMA foreign_keys = ON")

    # --- post-migration integrity + row-count report ---
    fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    after = counts(conn)
    trip_row = conn.execute(
        "SELECT currency, fx_to_eur FROM trip ORDER BY id LIMIT 1").fetchone()

    print(f"migrated {path} to user_version = 2")
    print(f"  trip currency/fx: {trip_row[0]}, {trip_row[1]}")
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
