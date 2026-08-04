"""One-off, idempotent update: Queenstown TOP 10 booked (deposit paid).

Booked direct at Queenstown TOP 10 Holiday Park (Arthurs Point): 2-BR unit,
2 nights 22-24 Feb 2027. Total tariff NZ$488.40. 25% deposit NZ$122.10 paid
now; balance NZ$366.30 auto-charges on 8 Feb 2027 (14 days before arrival).
Park policy: cancel/alter within 14 days of arrival = full tariff.

This replaces the pencilled "TOP 10 park-direct" placeholder: attaches a booked
accommodation cost to the Queenstown leg, rewrites the leg note, and trims the
lump "remaining accommodation" estimate by the 2 nights now booked (no double
count).

Run against the target DB via TRIPSITE_DB (defaults to ./data/trip.db):
  ./.venv/bin/python update_queenstown_nz.py
Idempotent: a second run makes no changes and logs no events. Requires a v3 DB.
"""

import os
import sys

try:
    import db  # noqa: E402
    connect, log_event = db.connect, db.log_event
except ModuleNotFoundError:
    import sqlite3
    from datetime import datetime, timezone, timedelta

    def connect():
        conn = sqlite3.connect(os.environ.get("TRIPSITE_DB", "./data/trip.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def log_event(conn, trip_id, person_id, summary):
        ts = datetime.now(timezone(timedelta(hours=2))).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO event (trip_id, ts, person_id, summary) VALUES (?, ?, ?, ?)",
            (trip_id, ts, person_id, summary),
        )

TRIP_NAME = "New Zealand 2027"

QT_COST_LABEL = "TOP 10 2-BR unit, NZ$488.40/2nt (deposit NZ$122.10 paid; balance NZ$366.30 auto-charges 8 Feb)"
QT_NOTES = (
    "Hub; TOP 10 2-BR unit GEBOEKT NZ$488,40/2nt (Arthurs Point), aanbetaling "
    "NZ$122,10 betaald; restant NZ$366,30 wordt automatisch afgeschreven 8 feb "
    "2027 (annuleren/wijzigen binnen 14 dagen = volledig tarief). Skyline "
    "Gondola + Luge, lakefront. Trimmed 3->2 to fund Dunedin."
)


def one(conn, q, args=()):
    return conn.execute(q, args).fetchone()


def main():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA user_version").fetchone()[0] < 3:
        sys.exit("DB is not v3.")

    trip = one(conn, "SELECT id FROM trip WHERE name = ?", (TRIP_NAME,))
    if not trip:
        sys.exit(f"Trip '{TRIP_NAME}' not found.")
    tid = trip["id"]
    pid_row = one(conn, "SELECT id FROM person WHERE name = 'Wiljan'")
    pid = pid_row["id"] if pid_row else None

    leg = one(conn, "SELECT id, notes FROM leg WHERE trip_id = ? AND name = 'Queenstown'", (tid,))
    if not leg:
        sys.exit("Queenstown leg not found.")
    lid = leg["id"]

    changes = []

    # 1. Booked accommodation cost on the Queenstown leg (only if not already there).
    existing = one(conn, "SELECT id FROM cost WHERE trip_id = ? AND leg_id = ? "
                         "AND category = 'accommodation'", (tid, lid))
    if not existing:
        conn.execute(
            "INSERT INTO cost (trip_id, label, amount, currency, kind, category, leg_id) "
            "VALUES (?, ?, ?, ?, 'booked', 'accommodation', ?)",
            (tid, QT_COST_LABEL, 488.40, "NZD", lid),
        )
        changes.append("Queenstown TOP 10 2-slaapkamer unit geboekt: NZ$488,40/2nt (22-24 feb), "
                       "aanbetaling NZ$122,10 betaald, restant NZ$366,30 afschrijving 8 feb.")

        # 2. Trim the lump "remaining accommodation" estimate by the 2 nights now booked,
        #    so those nights aren't counted twice. Only fires alongside the insert above.
        rem = one(conn, "SELECT id, amount, label FROM cost WHERE trip_id = ? AND leg_id IS NULL "
                        "AND category = 'accommodation' AND kind = 'estimated'", (tid,))
        if rem and round(rem["amount"], 2) == 6100.0:
            new_label = rem["label"].replace("~30 nights", "~28 nights")
            conn.execute("UPDATE cost SET amount = ?, label = ? WHERE id = ?",
                         (5612.0, new_label, rem["id"]))
            changes.append("Restschatting accommodatie verlaagd NZ$6.100 -> NZ$5.612 (~30 -> ~28 nachten, Queenstown eruit).")

    # 3. Rewrite the Queenstown leg note to reflect the booking.
    if leg["notes"] != QT_NOTES:
        conn.execute("UPDATE leg SET notes = ? WHERE id = ?", (QT_NOTES, lid))
        changes.append("Queenstown-notitie bijgewerkt: geboekt + afschrijfdatum 8 feb + annuleervoorwaarde.")

    for summary in changes:
        log_event(conn, tid, pid, summary)
    conn.commit()

    if changes:
        print(f"Applied {len(changes)} change(s) to trip {tid}:")
        for s in changes:
            print("  -", s)
    else:
        print("No changes needed (already up to date).")


if __name__ == "__main__":
    main()
