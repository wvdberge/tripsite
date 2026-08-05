"""One-off, idempotent update: record the Wanaka peak-price finding (Aug 2026).

Not booked. Price check for 24-26 Feb 2027 (2 nts, 2A+1C) shows Wanaka is
expensive on every channel. The former Wanaka TOP 10 has rebranded to Tasman
Holiday Parks -> no TOP 10 member discount there anymore. Rates found:
  Tasman Holiday Parks Wanaka: family studio NZ$363/nt, self-contained unit
  NZ$413/nt, cheapest cabin NZ$235/nt (shared bathroom + kitchen).
  Airbnb ~NZ$446/nt (~EUR250). Anything self-contained = ~EUR400-500 / 2 nts.

Records an *estimated* accommodation cost on the Wanaka leg anchored on the
family studio (NZ$726 / 2 nts, the best-value self-contained option) and writes
the finding + the open decision into the leg note. No booking made.

Run against the target DB via TRIPSITE_DB (defaults to ./data/trip.db):
  ./.venv/bin/python update_wanaka_nz.py
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

WANAKA_COST_LABEL = ("Est. accommodatie ~NZ$726/2nt (Tasman HP family studio $363/nt; "
                     "self-cont. unit $413; goedkoopste cabin $235 gedeeld; Airbnb ~$446). "
                     "Wanaka duur op alle kanalen — nog niet geboekt")
WANAKA_NOTES = (
    "Retreat: lakeside bach (Puzzling World, lakefront playground). Trimmed 3->2 "
    "to fund Dunedin. PRIJSCHECK aug 2026 (24-26 feb): Wanaka duur op alle "
    "kanalen. Ex-TOP 10 = nu Tasman Holiday Parks, GEEN member korting meer: "
    "family studio NZ$363/nt, self-contained unit $413/nt, goedkoopste cabin "
    "$235/nt (gedeelde badkamer/keuken). Airbnb ~$446/nt. Zelfstandig = "
    "~EUR400-500/2nt hoe dan ook. Beste waarde = family studio (~EUR406); echte "
    "besparing = bach in Albert Town/HAwea/Luggate 5-10 min buiten. "
    "NOG BESLISSEN: 2 nachten Wanaka waard direct na Queenstown (EUR488), of 1 "
    "nacht + herverdelen naar Dunedin/kust?"
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

    leg = one(conn, "SELECT id, notes FROM leg WHERE trip_id = ? AND name = 'Wanaka'", (tid,))
    if not leg:
        sys.exit("Wanaka leg not found.")
    lid = leg["id"]

    changes = []

    # 1. Estimated accommodation cost on the Wanaka leg (only if none there yet).
    existing = one(conn, "SELECT id FROM cost WHERE trip_id = ? AND leg_id = ? "
                         "AND category = 'accommodation'", (tid, lid))
    if not existing:
        conn.execute(
            "INSERT INTO cost (trip_id, label, amount, currency, kind, category, leg_id) "
            "VALUES (?, ?, ?, ?, 'estimated', 'accommodation', ?)",
            (tid, WANAKA_COST_LABEL, 726.0, "NZD", lid),
        )
        changes.append("Wanaka prijscheck: duur op alle kanalen. Schatting NZ$726/2nt "
                       "(family studio Tasman HP); unit $413/nt, cabin $235 gedeeld, "
                       "Airbnb ~$446/nt. Ex-TOP 10 -> Tasman HP, geen member korting. Niet geboekt.")

    # 2. Write the finding + open decision into the leg note.
    if leg["notes"] != WANAKA_NOTES:
        conn.execute("UPDATE leg SET notes = ? WHERE id = ?", (WANAKA_NOTES, lid))
        changes.append("Wanaka-notitie bijgewerkt met prijscheck en open vraag (2 nachten waard?).")

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
