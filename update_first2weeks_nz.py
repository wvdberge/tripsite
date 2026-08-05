"""One-off, idempotent update: rework the NZ 2027 first two weeks.

The flight shift left Christchurch too thin for recovery. Decision (Wiljan):
give Christchurch 3 nights and drop Dunedin/Otago, keeping Te Anau and every
downstream booking exactly as booked. Only the free-cancellation Twizel moves.

Net effect on the Christchurch -> Te Anau block (7 fixed nights, 12->19 Feb):
  before:  CHC 12-14 (2n) / Twizel 14-18 (4n, booked) / Dunedin 18-19 (1n)
  after :  CHC 12-15 (3n) / Twizel 15-19 (4n, rebook)  / Dunedin dropped
Te Anau (19-22, deposit paid) and all later legs are untouched.

The DB had Twizel as 13-17; the real booking is 14-18 (EUR486.53, free cancel).
This sets it to the target 15-19 regardless of the stale value.

Run against the target DB via TRIPSITE_DB:
  local dev:  ./.venv/bin/python update_first2weeks_nz.py
  live NAS :  TRIPSITE_DB=/volume1/docker/tripsite/data/trip.db python3 update_first2weeks_nz.py
Idempotent: a second run makes no changes and logs no events. Requires a v2 DB.
"""

import os
import sys

try:
    import db  # noqa: E402
    connect, log_event = db.connect, db.log_event
except ModuleNotFoundError:
    # The NAS host runs Python 3.8, which has no zoneinfo (db.py imports it).
    # Inline equivalents so the same script runs there. The event timestamp is
    # pinned to +02:00 (Amsterdam CEST, correct for a summer 2026 run).
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

CHC_NOTES = (
    "Arrival 12 Feb 12:50. Extended to 3 nights (12-15 Feb) for recovery after "
    "36h20 travel (13h10 HKG layover); keep the first day rustig. Car pickup now "
    "15 Feb (was 13). Margaret Mahy playground & Botanic Gardens."
)
TWIZEL_NOTES = (
    "Rebooked to 15-19 Feb (was 14-18), EUR486.53 (~EUR122/nt x4), free "
    "cancellation. Lands on Te Anau check-in 19 Feb (Dunedin dropped). Day-trip "
    "Tekapo (45min) + Mt Cook Hooker Valley (50min)."
)
TWIZEL_COST_LABEL = "Mountain Chalets Motel, EUR486.53/4nt (15-19 Feb)"

CAR_TASK = "Move SNAP car pickup to 15 Feb (Christchurch extended to 3 nights)"


def one(conn, q, args=()):
    return conn.execute(q, args).fetchone()


def main():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON")

    uv = conn.execute("PRAGMA user_version").fetchone()[0]
    if uv < 2:
        sys.exit(f"DB is v{uv}, expected v2.")

    trip = one(conn, "SELECT id FROM trip WHERE name = ?", (TRIP_NAME,))
    if not trip:
        sys.exit(f"Trip '{TRIP_NAME}' not found.")
    tid = trip["id"]

    wiljan = one(conn, "SELECT id FROM person WHERE name = 'Wiljan'")
    pid = wiljan["id"] if wiljan else None

    changes = []

    # 1. Christchurch -> 3 nights (12-15 Feb).
    chc = one(conn, "SELECT id, end_date FROM leg WHERE trip_id = ? AND name = 'Christchurch'", (tid,))
    if chc and chc["end_date"] != "2027-02-15":
        conn.execute("UPDATE leg SET start_date = ?, end_date = ?, notes = ? WHERE id = ?",
                     ("2027-02-12", "2027-02-15", CHC_NOTES, chc["id"]))
        changes.append("Christchurch verlengd naar 3 nachten (12-15 feb) voor herstel na de vlucht; SNAP-autopickup verschuift naar 15 feb.")

    # 2. Twizel -> 15-19 Feb (still 4 nights), price/label to the real booking.
    twz = one(conn, "SELECT id, start_date, end_date FROM leg WHERE trip_id = ? AND name LIKE 'Twizel%'", (tid,))
    if twz and (twz["start_date"] != "2027-02-15" or twz["end_date"] != "2027-02-19"):
        conn.execute("UPDATE leg SET start_date = ?, end_date = ?, notes = ? WHERE id = ?",
                     ("2027-02-15", "2027-02-19", TWIZEL_NOTES, twz["id"]))
        changes.append("Twizel omgeboekt naar 15-19 feb (was 14-18), EUR486,53, gratis annulering - bevestigd.")
    if twz:
        tc = one(conn, "SELECT id, amount, label FROM cost WHERE trip_id = ? AND leg_id = ? AND category = 'accommodation'", (tid, twz["id"]))
        if tc and (round(tc["amount"], 2) != 486.53 or tc["label"] != TWIZEL_COST_LABEL):
            conn.execute("UPDATE cost SET amount = ?, label = ? WHERE id = ?",
                         (486.53, TWIZEL_COST_LABEL, tc["id"]))
            changes.append("Twizel-kosten bijgewerkt naar geboekt bedrag EUR486,53.")

    # 3. Drop Dunedin/Otago. Unlink its ideas (keep them, mark rejected) first,
    #    then delete the leg so the FK check passes.
    dun = one(conn, "SELECT id FROM leg WHERE trip_id = ? AND name LIKE 'Dunedin%'", (tid,))
    if dun:
        ideas = conn.execute("SELECT id FROM idea WHERE leg_id = ?", (dun["id"],)).fetchall()
        for r in ideas:
            conn.execute("UPDATE idea SET leg_id = NULL, status = 'rejected' WHERE id = ?", (r["id"],))
        conn.execute("DELETE FROM leg WHERE id = ?", (dun["id"],))
        extra = f" ({len(ideas)} ideeën afgewezen: albatros/pinguin)" if ideas else ""
        changes.append(f"Dunedin/Otago geschrapt; die 2 nachten gaan naar Christchurch{extra}.")

    # 4. New task: move the car pickup (Twizel rebook is already done).
    exists = one(conn, "SELECT id FROM task WHERE trip_id = ? AND title = ?", (tid, CAR_TASK))
    if not exists:
        conn.execute("INSERT INTO task (trip_id, title, done) VALUES (?, ?, 0)", (tid, CAR_TASK))
        changes.append(f"Taak toegevoegd: {CAR_TASK}")

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
