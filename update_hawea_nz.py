"""One-off, idempotent update: swap Wanaka -> Lake Hawea (decided Aug 2026).

Decision: drop Wanaka (too expensive). This stretch becomes Hawea 2 + Haast 1.
Found a 3-bedroom house in Lake Hawea via Booking.com for EUR327 / 2 nts
(~EUR163/nt, ~half the Wanaka price), with free cancellation until February.
Enquiry sent 5 Aug 2026 -> not yet confirmed, so recorded as 'estimated'.

Changes:
- Rename the 'Wanaka' leg (id 6, 24-26 Feb) -> 'Lake Hawea'; rewrite the note.
- Replace the Wanaka price-check estimate (cost id 24, NZ$726) with the Hawea
  house EUR327/2nt (estimated: enquiry pending).
- Rename the 'West Coast (Haast/Fox)' leg -> 'Haast'; note its waypoint role,
  the two stop-clusters, and that Munro Beach penguins are off-season in Feb.
- Add follow-up tasks: confirm the Hawea booking; book the Haast night.

Run against the target DB via TRIPSITE_DB (defaults to ./data/trip.db):
  ./.venv/bin/python update_hawea_nz.py
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

HAWEA_NAME = "Lake Hāwea"
HAWEA_NOTES = (
    "Rustiger + goedkoper alternatief voor Wanaka (dat te duur was). 3-slaapkamer "
    "huis via Booking, EUR327/2nt (~EUR163/nt), GRATIS annuleren tot feb — enquiry "
    "verstuurd 5 aug 2026, nog te bevestigen. Lakefront rustdag/zwemmen; Wanaka "
    "(Puzzling World, winkels) 15 min. Daarna waypoint-nacht Haast richting Franz Josef."
)
HAWEA_COST_LABEL = ("3BR huis via Booking, EUR327/2nt (~EUR163/nt), gratis annuleren tot feb "
                    "— enquiry verstuurd, nog niet bevestigd")

HAAST_NAME = "Haast"
HAAST_NOTES = (
    "Waypoint-nacht richting Franz Josef (Hāwea->Franz ~4u + alle stops is te veel "
    "op één dag). Haast Pass cluster (Blue Pools, Fantail/Thunder Creek Falls) op "
    "de rit hierheen; Haast-kust cluster (Ship Creek, Knights Point) de volgende "
    "dag naar Franz. NB Munro Beach pinguïns alleen aug-nov, dus niet in feb. "
    "Haast-dorp = functionele motels — nog te boeken."
)

TASK_CONFIRM = "Bevestig Lake Hāwea 3BR huis (enquiry via Booking, gratis annuleren tot feb)"
TASK_HAAST = "Boek Haast waypoint-overnachting (26-27 feb, richting Franz Josef)"


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

    changes = []

    # 1. Rename Wanaka -> Lake Hāwea + rewrite note.
    wan = one(conn, "SELECT id, name, notes FROM leg WHERE trip_id = ? AND name = 'Wanaka'", (tid,))
    hawea = one(conn, "SELECT id, notes FROM leg WHERE trip_id = ? AND name = ?", (tid, HAWEA_NAME))
    leg = wan or hawea
    if not leg:
        sys.exit("Neither 'Wanaka' nor 'Lake Hāwea' leg found.")
    lid = leg["id"]
    if wan:
        conn.execute("UPDATE leg SET name = ?, notes = ? WHERE id = ?", (HAWEA_NAME, HAWEA_NOTES, lid))
        changes.append("Wanaka vervangen door Lake Hāwea (Wanaka te duur). Plan: Hāwea 2 + Haast 1.")
    elif leg["notes"] != HAWEA_NOTES:
        conn.execute("UPDATE leg SET notes = ? WHERE id = ?", (HAWEA_NOTES, lid))
        changes.append("Lake Hāwea-notitie bijgewerkt.")

    # 2. Swap the Wanaka price-check estimate for the Hāwea house (EUR327, still estimated).
    cost = one(conn, "SELECT id, amount, currency FROM cost WHERE trip_id = ? AND leg_id = ? "
                     "AND category = 'accommodation'", (tid, lid))
    if cost and (round(cost["amount"], 2) != 327.0 or cost["currency"] != "EUR"):
        conn.execute("UPDATE cost SET label = ?, amount = ?, currency = ?, kind = 'estimated' WHERE id = ?",
                     (HAWEA_COST_LABEL, 327.0, "EUR", cost["id"]))
        changes.append("Accommodatie-schatting Lake Hāwea: 3BR huis EUR327/2nt (~half Wanaka), "
                       "gratis annuleren tot feb, enquiry verstuurd — nog niet bevestigd.")
    elif not cost:
        conn.execute("INSERT INTO cost (trip_id, label, amount, currency, kind, category, leg_id) "
                     "VALUES (?, ?, ?, ?, 'estimated', 'accommodation', ?)",
                     (tid, HAWEA_COST_LABEL, 327.0, "EUR", lid))
        changes.append("Accommodatie-schatting Lake Hāwea toegevoegd: 3BR huis EUR327/2nt (enquiry).")

    # 3. Rename the Haast waypoint leg + note its role.
    haast = one(conn, "SELECT id, name, notes FROM leg WHERE trip_id = ? AND "
                      "(name = 'West Coast (Haast/Fox)' OR name = ?)", (tid, HAAST_NAME))
    if haast:
        if haast["name"] != HAAST_NAME or haast["notes"] != HAAST_NOTES:
            conn.execute("UPDATE leg SET name = ?, notes = ? WHERE id = ?", (HAAST_NAME, HAAST_NOTES, haast["id"]))
            changes.append("Waypoint-leg hernoemd naar 'Haast' + rol/stops genoteerd (pinguïns niet in feb).")

    # 4. Follow-up tasks.
    for title, msg in ((TASK_CONFIRM, "Taak toegevoegd: Hāwea-boeking bevestigen."),
                       (TASK_HAAST, "Taak toegevoegd: Haast-overnachting boeken.")):
        if not one(conn, "SELECT id FROM task WHERE trip_id = ? AND title = ?", (tid, title)):
            conn.execute("INSERT INTO task (trip_id, title, done) VALUES (?, ?, 0)", (tid, title))
            changes.append(msg)

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
