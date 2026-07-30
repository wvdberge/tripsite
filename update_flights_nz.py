"""One-off, idempotent update: reflect the booked NZ 2027 flights in the DB.

Cathay Pacific (all 4 segments CX, Economy Light) replaced the vervallen SIN
option. Depart AMS 10 Feb, arrive CHC 12 Feb; depart AKL 23 Mar. EUR 4,641.

Flight facts only. The itinerary tail rework (Christchurch now 1 night; +3
legless nights Mar 20-23) is deferred, so Auckland's leg end is left at Mar 20.

Run against the target DB via TRIPSITE_DB:
  local dev:  ./.venv/bin/python update_flights_nz.py
  live NAS :  inside the container, TRIPSITE_DB=/data/trip.db python update_flights_nz.py
Idempotent: a second run makes no changes and logs no events. Requires a v2 DB.
"""

import sys
import db

TRIP_NAME = "New Zealand 2027"


def one(conn, q, args=()):
    r = conn.execute(q, args).fetchone()
    return r


def main():
    conn = db.connect()
    conn.execute("PRAGMA foreign_keys = ON")

    uv = conn.execute("PRAGMA user_version").fetchone()[0]
    if uv < 2:
        sys.exit(f"DB is v{uv}, expected v2. Run the deferred migrate_v2.py first.")

    trip = one(conn, "SELECT id, start_date, end_date FROM trip WHERE name = ?", (TRIP_NAME,))
    if not trip:
        sys.exit(f"Trip '{TRIP_NAME}' not found.")
    tid = trip["id"]

    wiljan = one(conn, "SELECT id FROM person WHERE name = 'Wiljan'")
    pid = wiljan["id"] if wiljan else None

    changes = []  # (summary) logged as events only for real changes

    # 1. Trip dates: AMS departure 10 Feb, AKL departure 23 Mar.
    if trip["start_date"] != "2027-02-10" or trip["end_date"] != "2027-03-23":
        conn.execute("UPDATE trip SET start_date = ?, end_date = ? WHERE id = ?",
                     ("2027-02-10", "2027-03-23", tid))
        changes.append("Trip-datums bijgesteld naar vluchtboeking: 10 feb (vertrek AMS) - 23 mrt (vertrek AKL).")

    # 2. Christchurch leg: arrival now 12 Feb (1 night before car pickup 13 Feb).
    chc = one(conn, "SELECT id, start_date, end_date, notes FROM leg WHERE trip_id = ? AND name = 'Christchurch'", (tid,))
    if chc and chc["start_date"] != "2027-02-12":
        new_notes = ("Arrival 12 Feb 12:50 (was 10 Feb). Now 1 night before car pickup 13 Feb "
                     "-> thin recovery after 36h20 travel (13h10 HKG layover); keep the first day rustig. "
                     "Margaret Mahy playground & Botanic Gardens.")
        conn.execute("UPDATE leg SET start_date = ?, notes = ? WHERE id = ?",
                     ("2027-02-12", new_notes, chc["id"]))
        changes.append("Christchurch verkort naar 1 nacht (aankomst 12 feb i.p.v. 10 feb).")

    # 3. Resync day rows to the new Feb 10 - Mar 23 range (drop Feb 08-09, add Mar 21-23).
    from datetime import date, timedelta
    have = {r["date"] for r in conn.execute("SELECT date FROM day WHERE trip_id = ?", (tid,))}
    want = set()
    d, last = date(2027, 2, 10), date(2027, 3, 23)
    while d <= last:
        want.add(d.isoformat())
        d += timedelta(days=1)
    to_add = sorted(want - have)
    to_del = sorted(have - want)
    for iso in to_add:
        conn.execute("INSERT INTO day (trip_id, date) VALUES (?, ?)", (tid, iso))
    for iso in to_del:
        conn.execute("DELETE FROM day WHERE trip_id = ? AND date = ?", (tid, iso))
    if to_add or to_del:
        changes.append(f"Dagen gesynct naar 10 feb-23 mrt (+{len(to_add)} / -{len(to_del)}).")

    # 4. Flight cost: booked, EUR 4,641, Cathay via HKG.
    fc = one(conn, "SELECT id, label, amount, kind FROM cost WHERE trip_id = ? AND category = 'transport' "
                   "AND label LIKE 'Flights%'", (tid,))
    new_label = "Flights AMS<->CHC/AKL via HKG, 3 pax (Cathay, Economy Light)"
    if fc and (round(fc["amount"]) != 4641 or fc["kind"] != "booked" or fc["label"] != new_label):
        conn.execute("UPDATE cost SET label = ?, amount = ?, kind = ? WHERE id = ?",
                     (new_label, 4641, "booked", fc["id"]))
        changes.append("Vluchten geboekt: Cathay EUR 4.641 (was schatting EUR 5.427 via SIN).")

    # 5. Flight task: done.
    ft = one(conn, "SELECT id, title, done FROM task WHERE trip_id = ? AND title LIKE 'Book flights%'", (tid,))
    if ft and not ft["done"]:
        conn.execute("UPDATE task SET title = ?, done = 1 WHERE id = ?",
                     ("Flights booked (Cathay EUR 4,641 via HKG; 10 Feb dep / 23 Mar ret)", ft["id"]))
        changes.append("Taak 'vluchten boeken' afgevinkt.")

    # 6. Tail-reallocation task: note the +3 nights from the later return.
    tt = one(conn, "SELECT id, title FROM task WHERE trip_id = ? AND title LIKE '%reallocation%'", (tid,))
    new_tt = ("Rework tail: return moved to 23 Mar, so +3 nights to place (Mar 20-23 now legless) "
              "on top of the TBD 2 (Coromandel / Auckland / Taupo)")
    if tt and tt["title"] != new_tt:
        conn.execute("UPDATE task SET title = ? WHERE id = ?", (new_tt, tt["id"]))
        changes.append("Staart-taak bijgewerkt: +3 nachten te verdelen (vertrek 23 mrt).")

    for summary in changes:
        db.log_event(conn, tid, pid, summary)

    conn.commit()

    if changes:
        print(f"Applied {len(changes)} change(s) to trip {tid}:")
        for s in changes:
            print("  -", s)
    else:
        print("No changes needed (already up to date).")


if __name__ == "__main__":
    main()
