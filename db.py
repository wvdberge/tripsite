"""SQLite access: connection, schema init, event logging, small helpers.

The DB path comes from the TRIPSITE_DB env var (set in the container to
/data/trip.db). Locally it defaults to ./data/trip.db next to this file.
"""

import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

AMS = ZoneInfo("Europe/Amsterdam")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "data", "trip.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")


def db_path():
    return os.environ.get("TRIPSITE_DB", DEFAULT_DB)


def connect():
    """Open a connection with row access by name and foreign keys enforced."""
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    """Create all tables from schema.sql (no-op if they already exist)."""
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()


def now_iso():
    # Store local wall-clock time. The container runs in UTC, so relying on
    # astimezone() gave timestamps 2h behind Amsterdam (the feed truncates the
    # offset). Pin the zone explicitly; DST is handled by ZoneInfo.
    return datetime.now(AMS).isoformat(timespec="seconds")


def log_event(conn, trip_id, person_id, summary):
    """Append one human-readable feed event. Caller commits."""
    conn.execute(
        "INSERT INTO event (trip_id, ts, person_id, summary) VALUES (?, ?, ?, ?)",
        (trip_id, now_iso(), person_id, summary),
    )
