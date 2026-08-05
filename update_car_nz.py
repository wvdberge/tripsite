"""One-off, idempotent update: reflect the SNAP car booked directly.

Booked at SNAP: Toyota Corolla hatch (2019-2023 or similar), CHC airport pickup
12 Feb 2027 13:30 -> AKL airport drop-off 23 Mar 13:30. Limited Cover, +1 driver,
booster seat (4+, fine: he turns 4 in Mar and is tall). NZ$2,198.84, pay at
pickup. Replaces the rentalcars.com route (Wiljan cancels that). The DB estimate
was EUR1,815 / Mitsubishi ASX; actual NZ$2,198.84 ~= EUR1,231.

Pickup is on arrival (12 Feb), so the earlier "move pickup to 15 Feb" task is void.

Run against the target DB via TRIPSITE_DB (defaults to ./data/trip.db):
  ./.venv/bin/python update_car_nz.py
Idempotent: a second run makes no changes and logs no events. Requires a v2 DB.
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

CAR_LABEL = ("Car hire — SNAP Toyota Corolla hatch (CHC airport 12 Feb -> AKL "
             "airport 23 Mar; Limited Cover, +1 driver, booster seat; pay at pickup)")
CHC_NOTES = (
    "Arrival 12 Feb 12:50. Extended to 3 nights (12-15 Feb) for recovery after "
    "36h20 travel (13h10 HKG layover); keep the first day rustig. Car pickup 12 "
    "Feb 13:30 at CHC airport on arrival (SNAP). Margaret Mahy playground & "
    "Botanic Gardens."
)
RENTALCARS_TASK = "Confirm the rentalcars.com car booking is cancelled (no charge)"
OLD_PICKUP_TASK = "Move SNAP car pickup to 15 Feb (Christchurch extended to 3 nights)"


def one(conn, q, args=()):
    return conn.execute(q, args).fetchone()


def main():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA user_version").fetchone()[0] < 2:
        sys.exit("DB is not v2.")

    trip = one(conn, "SELECT id FROM trip WHERE name = ?", (TRIP_NAME,))
    if not trip:
        sys.exit(f"Trip '{TRIP_NAME}' not found.")
    tid = trip["id"]
    pid_row = one(conn, "SELECT id FROM person WHERE name = 'Wiljan'")
    pid = pid_row["id"] if pid_row else None

    changes = []

    # 1. Car cost -> actual SNAP booking (NZD, booked).
    car = one(conn, "SELECT id, label, amount, currency, kind FROM cost WHERE trip_id = ? "
                    "AND category = 'transport' AND label LIKE 'Car hire%'", (tid,))
    if car and (car["label"] != CAR_LABEL or round(car["amount"], 2) != 2198.84
                or car["currency"] != "NZD" or car["kind"] != "booked"):
        conn.execute("UPDATE cost SET label = ?, amount = ?, currency = ?, kind = ? WHERE id = ?",
                     (CAR_LABEL, 2198.84, "NZD", "booked", car["id"]))
        changes.append("Auto direct bij SNAP geboekt: Toyota Corolla hatch, CHC-airport 12 feb -> AKL-airport 23 mrt, NZ$2.198,84 (was schatting EUR1.815), betalen bij ophalen.")

    # 2. Christchurch note: pickup is 12 Feb on arrival, not 15 Feb.
    chc = one(conn, "SELECT id, notes FROM leg WHERE trip_id = ? AND name = 'Christchurch'", (tid,))
    if chc and chc["notes"] != CHC_NOTES:
        conn.execute("UPDATE leg SET notes = ? WHERE id = ?", (CHC_NOTES, chc["id"]))
        changes.append("Autopickup gecorrigeerd naar 12 feb 13:30 op CHC-airport (bij aankomst).")

    # 3. Obsolete "move pickup to 15 Feb" task -> gone (pickup is 12 Feb).
    old = one(conn, "SELECT id FROM task WHERE trip_id = ? AND title = ?", (tid, OLD_PICKUP_TASK))
    if old:
        conn.execute("DELETE FROM task WHERE id = ?", (old["id"],))
        changes.append("Taak 'autopickup verplaatsen naar 15 feb' vervallen (ophalen is 12 feb).")

    # 4. Child-seat task done (booster booked).
    seat = one(conn, "SELECT id, done FROM task WHERE trip_id = ? AND title LIKE '%child seat%'", (tid,))
    if seat and not seat["done"]:
        conn.execute("UPDATE task SET done = 1 WHERE id = ?", (seat["id"],))
        changes.append("Taak 'kinderzitje reserveren' afgevinkt (boosterzitje 4+ geboekt).")

    # 5. Rentalcars cancellation follow-up.
    if not one(conn, "SELECT id FROM task WHERE trip_id = ? AND title = ?", (tid, RENTALCARS_TASK)):
        conn.execute("INSERT INTO task (trip_id, title, done) VALUES (?, ?, 0)", (tid, RENTALCARS_TASK))
        changes.append(f"Taak toegevoegd: {RENTALCARS_TASK}")

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
