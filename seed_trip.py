"""Seed one trip into the DB from a module in seed/trips/. Additive — never wipes.

Usage:
    python seed_trip.py <module> [--partner "Name"]
    e.g.  python seed_trip.py uk2026

Refuses if a trip with the module's name already exists (so a re-run is a no-op,
not a duplicate). Creates missing people but never duplicates them. Honors
TRIPSITE_DB. On a fresh DB it also creates the v2 schema via db.init_schema.
"""

import argparse
import importlib
import sys
from datetime import date, timedelta

import db
from seed.places import coords


def daterange(start_iso, end_iso):
    d = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def ensure_person(conn, name):
    """Return the id of the person named `name`, creating the row if needed."""
    row = conn.execute("SELECT id FROM person WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO person (name) VALUES (?)", (name,)).lastrowid


def run(module_name, partner):
    mod = importlib.import_module(f"seed.trips.{module_name}")
    TRIP, LEGS = mod.TRIP, mod.LEGS
    COSTS, TASKS, IDEAS = mod.COSTS, mod.TASKS, mod.IDEAS

    conn = db.connect()
    # Create the v2 schema only on a genuinely fresh DB; never re-run it (that would
    # re-stamp PRAGMA user_version and error on the plain CREATE TABLE statements).
    fresh = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip'").fetchone()
    if not fresh:
        db.init_schema(conn)

    if conn.execute("SELECT 1 FROM trip WHERE name = ?", (TRIP["name"],)).fetchone():
        print(f"Refusing: a trip named {TRIP['name']!r} already exists.",
              file=sys.stderr)
        conn.close()
        sys.exit(1)

    cur = conn.execute(
        "INSERT INTO trip (name, start_date, end_date, currency, fx_to_eur, budget_eur) "
        "VALUES (?,?,?,?,?,?)",
        (TRIP["name"], TRIP["start_date"], TRIP["end_date"], TRIP["currency"],
         TRIP["fx_to_eur"], TRIP.get("budget_eur")))
    tid = cur.lastrowid

    # People are global. Wiljan authors the seeded ideas; the partner is optional.
    author_id = ensure_person(conn, "Wiljan")
    if partner:
        ensure_person(conn, partner)

    leg_ids = {}
    for (seq, name, place_key, location, start, end, accom, status, ref, notes) in LEGS:
        lat, lon = coords(place_key) if place_key else (None, None)
        c = conn.execute(
            "INSERT INTO leg (trip_id, seq, name, location, lat, lon, start_date, "
            "end_date, accommodation, accommodation_status, confirmation_ref, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, seq, name, location, lat, lon, start, end, accom, status, ref, notes))
        leg_ids[name] = c.lastrowid

    n_days = 0
    for iso in daterange(TRIP["start_date"], TRIP["end_date"]):
        conn.execute("INSERT INTO day (trip_id, date) VALUES (?, ?)", (tid, iso))
        n_days += 1

    for (label, amount, currency, kind, category, leg_key) in COSTS:
        conn.execute(
            "INSERT INTO cost (trip_id, label, amount, currency, kind, category, leg_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (tid, label, amount, currency, kind, category,
             leg_ids.get(leg_key) if leg_key else None))

    for (title, leg_key) in TASKS:
        conn.execute(
            "INSERT INTO task (trip_id, title, leg_id) VALUES (?, ?, ?)",
            (tid, title, leg_ids.get(leg_key) if leg_key else None))

    created = db.now_iso()
    for (title, place_key, leg_key, notes) in IDEAS:
        lat, lon = coords(place_key) if place_key else (None, None)
        conn.execute(
            "INSERT INTO idea (trip_id, title, location, lat, lon, notes, status, "
            "author_id, leg_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (tid, title, place_key, lat, lon, notes, "idea", author_id,
             leg_ids.get(leg_key), created))

    db.log_event(conn, tid, author_id,
                 f"Seeded {TRIP['name']}: {len(LEGS)} legs, {n_days} days, "
                 f"{len(IDEAS)} ideas, {len(TASKS)} tasks")
    conn.commit()

    def count(t):
        return conn.execute(
            f"SELECT COUNT(*) AS n FROM {t} WHERE trip_id = ?", (tid,)).fetchone()["n"]

    print(f"Seeded trip {TRIP['name']!r} (id {tid}). Row counts for this trip:")
    for t in ("leg", "day", "idea", "cost", "task"):
        print(f"  {t:6s} {count(t)}")
    conn.close()


def main():
    ap = argparse.ArgumentParser(description="Seed one trip into the DB (additive).")
    ap.add_argument("module", help="module name under seed/trips/, e.g. uk2026")
    ap.add_argument("--partner", default=None,
                    help="also ensure a person with this name exists")
    args = ap.parse_args()
    run(args.module, args.partner)


if __name__ == "__main__":
    main()
