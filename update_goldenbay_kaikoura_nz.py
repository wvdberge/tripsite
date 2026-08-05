"""One-off, idempotent update: Golden Bay + Kaikoura insert (Aug 2026).

Reworks the South Island tail and shifts the North Island later. Decided with
Wiljan: add Golden Bay (2n) and Kaikoura (2n), and replace the old Nelson
recovery night with a Blenheim drive-splitter that breaks the long Golden
Bay -> Kaikoura run (~5h) into ~3h + ~2h. Kaikoura -> Picton is ~2h to the
ferry. Funded by the 2 parked TBD nights + the 3 nights freed when the return
moved to Mar 23; Auckland grows 2 -> 3 nights so the chain lands on the Mar 23
flight. Total stays 39 nights (checkout Mar 23).

New South Island tail (seq 9 is the booked Bark Bay campsite, unchanged):
  10 Golden Bay            Mar 6  -> Mar 8   (2n, NEW)
  11 Blenheim (Marlb.)     Mar 8  -> Mar 9   (1n, was Nelson)
  12 Kaikoura              Mar 9  -> Mar 11  (2n, NEW)
  13 Wellington            Mar 11 -> Mar 13  (ferry Mar 11)
  14 Taupo                 Mar 13 -> Mar 15
  15 Rotorua               Mar 15 -> Mar 17
  16 Coromandel            Mar 17 -> Mar 20
  17 Auckland              Mar 20 -> Mar 23  (now 3n)
The old TBD placeholder leg is removed; its "rework tail" task is marked done.

Run against the target DB via TRIPSITE_DB (defaults to ./data/trip.db):
  ./.venv/bin/python update_goldenbay_kaikoura_nz.py          # local copy
  TRIPSITE_DB=./data/trip.db python3 update_goldenbay_kaikoura_nz.py   # on NAS
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

GOLDEN_BAY_NOTES = (
    "NEW (aug 2026). Post-camp herstelbasis: echt bed/douche/was/resupply na 2 "
    "nachten Bark Bay DOC. Over Takaka Hill ~1u15 vanaf Marahau na de 12:45 "
    "watertaxi-pickup Mar 6. Basis Pohara/Takaka. Doen: Te Waikoropupu (Pupu) "
    "Springs (helderste zoetwater, vlakke 30-min loop), Wharariki Beach (Archway "
    "Islands + zeehondenpups in de rotspoelen bij laag water), Anatoki tamme palingen "
    "+ zalm (kinderhit), Farewell Spit. Doodlopende omweg (terug over de hill). "
    "Accommodatie nog te boeken."
)
BLENHEIM_NOTES = (
    "NEW (aug 2026) - vervangt de oude Nelson-herstelnacht. Rit-splitser Golden "
    "Bay->Kaikoura: breekt de ~5u run in ~3u (naar Blenheim) + ~2u (naar Kaikoura). "
    "Marlborough wijnstreek; optioneel Omaka Aviation Heritage Centre (kids). "
    "Accommodatie nog te boeken. Alt: splitsen bij Nelson kan ook."
)
KAIKOURA_NOTES = (
    "NEW (aug 2026) - un-rejected nadat Dunedin verviel, dus Kaikoura wordt de "
    "wildlife-hoofdstop. Doen: whale watching, zeehondenkolonie + pups bij Point "
    "Kean / Ohau Stream, Kaikoura Peninsula walkway. ~2u naar Picton voor de ferry "
    "-> uitrusten op de overtocht. Accommodatie nog te boeken."
)
WELLINGTON_NOTES = (
    "Rij Kaikoura->Picton (~2u) Mar 11 + Cook Strait ferry (Interislander "
    "Picton->Wgtn, TOP 10 10% geldt). Te Papa Museum (kids' Discovery Centres). "
    "Ferry verschoven Mar 7->Mar 11 door de Golden Bay/Blenheim/Kaikoura-invoeging."
)
AUCKLAND_NOTES = (
    "Laatste nachten (nu 3: Mar 20-23) voor het vertrek AKL->AMS op Mar 23. Sky "
    "Tower of Mission Bay. Extra nacht uit de tail-herverdeling."
)

# Desired final state, keyed by canonical leg name. lat/lon on the 3 new legs so
# the map renders. NI legs: only seq + dates change (+ note for Wgtn/Auckland).
NEW_LEGS = [
    dict(name="Golden Bay", location="Takaka, Golden Bay, New Zealand",
         lat=-40.8510, lon=172.8080, seq=10,
         start_date="2027-03-06", end_date="2027-03-08", notes=GOLDEN_BAY_NOTES),
    dict(name="Kaikoura", location="Kaikoura, New Zealand",
         lat=-42.3990, lon=173.6810, seq=12,
         start_date="2027-03-09", end_date="2027-03-11", notes=KAIKOURA_NOTES),
]
BLENHEIM = dict(name="Blenheim (Marlborough)", location="Blenheim, New Zealand",
                lat=-41.5140, lon=173.9610, seq=11,
                start_date="2027-03-08", end_date="2027-03-09", notes=BLENHEIM_NOTES)
# NI legs to reseq + redate (name is the lookup key; None note = leave as-is).
RESHIFT = [
    dict(name="Wellington", seq=13, start_date="2027-03-11", end_date="2027-03-13",
         notes=WELLINGTON_NOTES),
    dict(name="Taupo", seq=14, start_date="2027-03-13", end_date="2027-03-15", notes=None),
    dict(name="Rotorua", seq=15, start_date="2027-03-15", end_date="2027-03-17", notes=None),
    dict(name="Coromandel", seq=16, start_date="2027-03-17", end_date="2027-03-20", notes=None),
    dict(name="Auckland", seq=17, start_date="2027-03-20", end_date="2027-03-23",
         notes=AUCKLAND_NOTES),
]


def one(conn, q, args=()):
    return conn.execute(q, args).fetchone()


def leg_by_name(conn, tid, name):
    return one(conn, "SELECT * FROM leg WHERE trip_id = ? AND name = ?", (tid, name))


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

    # 1. Insert Golden Bay + Kaikoura (or converge them if a prior run made them).
    for spec in NEW_LEGS:
        row = leg_by_name(conn, tid, spec["name"])
        if not row:
            conn.execute(
                "INSERT INTO leg (trip_id, seq, name, location, lat, lon, start_date, "
                "end_date, accommodation_status, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tbd', ?)",
                (tid, spec["seq"], spec["name"], spec["location"], spec["lat"],
                 spec["lon"], spec["start_date"], spec["end_date"], spec["notes"]),
            )
            changes.append(f"{spec['name']} toegevoegd (seq {spec['seq']}, "
                           f"{spec['start_date']}->{spec['end_date']}, 2 nachten).")
        else:
            conn.execute(
                "UPDATE leg SET seq=?, location=?, lat=?, lon=?, start_date=?, "
                "end_date=?, notes=? WHERE id=?",
                (spec["seq"], spec["location"], spec["lat"], spec["lon"],
                 spec["start_date"], spec["end_date"], spec["notes"], row["id"]),
            )

    # 2. Nelson (recovery) -> Blenheim (Marlborough). Nelson has no attachments.
    nelson = leg_by_name(conn, tid, "Nelson (recovery)")
    blen = leg_by_name(conn, tid, BLENHEIM["name"])
    if nelson and not blen:
        conn.execute(
            "UPDATE leg SET seq=?, name=?, location=?, lat=?, lon=?, start_date=?, "
            "end_date=?, accommodation_status='tbd', notes=? WHERE id=?",
            (BLENHEIM["seq"], BLENHEIM["name"], BLENHEIM["location"], BLENHEIM["lat"],
             BLENHEIM["lon"], BLENHEIM["start_date"], BLENHEIM["end_date"],
             BLENHEIM["notes"], nelson["id"]),
        )
        changes.append("Nelson-herstelnacht omgezet naar Blenheim (Marlborough), "
                       "seq 11, 2027-03-08->09, als rit-splitser naar Kaikoura.")
    elif not blen:
        conn.execute(
            "INSERT INTO leg (trip_id, seq, name, location, lat, lon, start_date, "
            "end_date, accommodation_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tbd', ?)",
            (tid, BLENHEIM["seq"], BLENHEIM["name"], BLENHEIM["location"], BLENHEIM["lat"],
             BLENHEIM["lon"], BLENHEIM["start_date"], BLENHEIM["end_date"], BLENHEIM["notes"]),
        )
        changes.append("Blenheim (Marlborough) toegevoegd (seq 11).")

    # 3. Reseq + redate the North Island legs (+ notes on Wellington / Auckland).
    for spec in RESHIFT:
        row = leg_by_name(conn, tid, spec["name"])
        if not row:
            print(f"  ! warning: NI leg '{spec['name']}' not found, skipped")
            continue
        moved = row["seq"] != spec["seq"] or row["start_date"] != spec["start_date"] \
            or row["end_date"] != spec["end_date"]
        if spec["notes"] is None:
            conn.execute("UPDATE leg SET seq=?, start_date=?, end_date=? WHERE id=?",
                         (spec["seq"], spec["start_date"], spec["end_date"], row["id"]))
        else:
            conn.execute("UPDATE leg SET seq=?, start_date=?, end_date=?, notes=? WHERE id=?",
                         (spec["seq"], spec["start_date"], spec["end_date"],
                          spec["notes"], row["id"]))
        if moved:
            changes.append(f"{spec['name']} verschoven -> seq {spec['seq']}, "
                           f"{spec['start_date']}->{spec['end_date']}.")

    # 4. Remove the TBD placeholder leg; mark its 'rework tail' task done + unlink.
    tbd = leg_by_name(conn, tid, "TBD (2 nights to reallocate)")
    if tbd:
        conn.execute(
            "UPDATE task SET done=1, leg_id=NULL WHERE leg_id=? AND title LIKE 'Rework tail%'",
            (tbd["id"],),
        )
        # any other stragglers pointing at the placeholder get unlinked, not lost
        conn.execute("UPDATE task SET leg_id=NULL WHERE leg_id=?", (tbd["id"],))
        conn.execute("UPDATE idea SET leg_id=NULL WHERE leg_id=?", (tbd["id"],))
        conn.execute("UPDATE cost SET leg_id=NULL WHERE leg_id=?", (tbd["id"],))
        conn.execute("DELETE FROM leg WHERE id=?", (tbd["id"],))
        changes.append("TBD-placeholder leg verwijderd; 'rework tail' taak op done gezet "
                       "(nachten opgegaan in Golden Bay/Blenheim/Kaikoura + Auckland +1).")

    # Integrity check before commit.
    bad = conn.execute("PRAGMA foreign_key_check").fetchall()
    if bad:
        conn.rollback()
        sys.exit(f"foreign_key_check failed, rolled back: {[tuple(b) for b in bad]}")

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
