"""UK Cycling 2026 — Hadrian's Cycleway (NCN 72). Transcribed from
../uk_cycling/itinerary.md, costs.md and hotel.md (those are authoritative).
Consumed by seed_trip.py.

16 days, West-to-East, IJmuiden <-> Newcastle by DFDS ferry. Family of three
(2 adults + toddler) + Thule trailer (converts to stroller for train and ferry).
Costs are stored in EUR (the figures in costs.md); GBP originals are noted in
the label. trip.currency is GBP with fx 1.1711 so the add-cost form and FX box
still offer GBP.

Tuple formats (shared by every trip module):
  LEGS:  (seq, name, place_key, location, start, end, accom, status, ref, notes)
  COSTS: (label, amount, currency, kind, category, leg_key or None)
  TASKS: (title, leg_key or None)
  IDEAS: (title, place_key or None, leg_key, notes)
"""

TRIP = {
    "name": "UK Cycling 2026 — Hadrian's Cycleway",
    "start_date": "2026-08-20",   # board ferry at IJmuiden
    "end_date": "2026-09-04",     # ferry arrives back in IJmuiden
    "currency": "GBP",
    "fx_to_eur": 1.1711,          # EUR per GBP (Jul 24, 2026)
    "budget_eur": 3365,
}

# 8 legs (where you sleep each night). All accommodation booked.
LEGS = [
    (1, "DFDS ferry (outbound)", "North Shields", "IJmuiden → Newcastle",
     "2026-08-20", "2026-08-21", "DFDS overnight ferry cabin", "booked", None,
     "Board IJmuiden 17:30, arrive North Shields 09:15. Thule in stroller mode "
     "for boarding and stowage. Then ~15 km up the Tyne on NCN72 into Newcastle."),
    (2, "Newcastle (arrival)", "Newcastle", "Quayside, Newcastle upon Tyne",
     "2026-08-21", "2026-08-22", "Premier Inn Millennium Bridge", "booked", None,
     "City Road, Quayside (NE1 2AN). Family room, bikes in room — request ground "
     "floor and flag the Thule. Recover from the ferry, explore the Quayside."),
    (3, "Carlisle", "Carlisle", "Carlisle",
     "2026-08-22", "2026-08-24", "Brooklyn House", "booked", None,
     "Cycling-specialist guest house, secure CCTV locked yard. Day 3: train "
     "Newcastle→Carlisle (Thule to stroller mode). Day 4: Solway Coast loop to "
     "Bowness-on-Solway (~52 km, exceptionally flat) — the western end of the Wall."),
    (4, "Brampton", "Brampton", "Brampton",
     "2026-08-24", "2026-08-26", "Scotch Arms Mews", "booked", None,
     "35 Main Street. B&B with breakfast, secure indoor bike storage + drying "
     "room. Carlisle→Brampton ~25 km, gentle rolling. Discovery loop (~30 km): "
     "Lanercost Priory + Talkin Tarn."),
    (5, "Haltwhistle", "Haltwhistle", "Coanwood, near Haltwhistle",
     "2026-08-26", "2026-08-28", "Hillis Close Farm Cottage", "booked", None,
     "Working farm ~4 miles from Haltwhistle, self-catering, inglenook fireplace. "
     "Brampton→Haltwhistle ~28 km. South Tyne loop (~42 km): Lambley Viaduct + "
     "Roman Army Museum at Walltown."),
    (6, "Hexham", "Hexham", "Hexham",
     "2026-08-28", "2026-08-31", "Abbey Apartment", "booked", None,
     "Self-catering, 3 nights — a deliberate recovery buffer, do not shrink it. "
     "Haltwhistle→Hexham ~35 km is the hilly Military Road section (Vindolanda, "
     "Housesteads). Rest day + optional Corbridge loop."),
    (7, "Newcastle (end)", "Newcastle", "Jesmond, Newcastle upon Tyne",
     "2026-08-31", "2026-09-03", "Caledonian Hotel", "booked", None,
     "Osborne Road, Jesmond (NE2 2AT). 3 nights, breakfast, 1 mile to centre. "
     "Hexham→Newcastle ~40 km, mostly flat/downhill along the Tyne. Rest + spare "
     "days: Discovery Museum, Great North Museum, Tynemouth beach."),
    (8, "DFDS ferry (return)", "North Shields", "Newcastle → IJmuiden",
     "2026-09-03", "2026-09-04", "DFDS overnight ferry cabin", "booked", None,
     "Check out Sep 3, final ~15 km ride to North Shields, board 17:00. Thule to "
     "stroller mode for stowage. Arrive IJmuiden 09:45 on Sep 4."),
]

# Costs in EUR (costs.md figures). Booked = 698 + 1707 = 2405; est = 960; total 3365.
COSTS = [
    ("DFDS return ferry (Option 2, all-in)", 698, "EUR", "booked", "transport", None),
    ("Premier Inn Millennium Bridge, 1nt (£67)", 78, "EUR", "booked",
     "accommodation", "Newcastle (arrival)"),
    ("Brooklyn House, 2nt", 242, "EUR", "booked", "accommodation", "Carlisle"),
    ("Scotch Arms Mews, 2nt B&B (£276)", 323, "EUR", "booked",
     "accommodation", "Brampton"),
    ("Hillis Close Farm Cottage, 2nt", 277, "EUR", "booked",
     "accommodation", "Haltwhistle"),
    ("Abbey Apartment, 3nt", 440, "EUR", "booked", "accommodation", "Hexham"),
    ("Caledonian Hotel, 3nt", 347, "EUR", "booked",
     "accommodation", "Newcastle (end)"),
    ("Trains & misc transport (Newcastle→Carlisle etc.)", 100, "EUR",
     "estimated", "transport", None),
    ("Food & activities (~€60/day, self-catering + pubs)", 860, "EUR",
     "estimated", "food", None),
]

TASKS = [
    ("Confirm the DFDS balance was paid (full payment was due Jul 21, 2026)",
     "DFDS ferry (outbound)"),
    ("Book the Newcastle → Carlisle train (Aug 22; bikes + Thule in stroller mode)",
     "Carlisle"),
    ("Confirm bike storage at Hillis Close Farm on arrival", "Haltwhistle"),
]

# Ideas attach to legs. location strings are not in seed/places.py, so they carry
# no map pin (leg markers show the corridor); eyeball/add coords later if wanted.
IDEAS = [
    ("Solway Coast loop to Bowness-on-Solway", "Bowness-on-Solway", "Carlisle",
     "Out-and-back on NCN72 (~52 km), flat quiet lanes through salt marshes; the "
     "official western end of Hadrian's Wall."),
    ("Lanercost Priory", "Lanercost", "Brampton",
     "12th-century priory ruins on the Brampton discovery loop."),
    ("Talkin Tarn Country Park", "Talkin Tarn", "Brampton",
     "Lakeside country park; a play break for the child."),
    ("South Tyne loop / Lambley Viaduct", "Lambley Viaduct", "Haltwhistle",
     "Hard-packed former railway line (~42 km); panoramic valley views from the viaduct."),
    ("Roman Army Museum (Walltown)", "Walltown", "Haltwhistle",
     "Roman kit and film; near the South Tyne loop."),
    ("Vindolanda", "Vindolanda", "Hexham",
     "Active dig on the Military Road section; writing tablets, kid-friendly."),
    ("Housesteads Roman Fort", "Housesteads", "Hexham",
     "Best-preserved Wall fort; on the Haltwhistle→Hexham route."),
    ("Hexham Abbey", "Hexham Abbey", "Hexham",
     "Anglo-Saxon crypt; central, an easy rest-day walk."),
    ("Corbridge loop", "Corbridge", "Hexham",
     "Short ride to the historic village of Corbridge (optional Hexham day)."),
    ("Dilston Physic Garden", "Dilston", "Hexham",
     "Small medicinal-plant garden near Hexham; low-key rest-day option."),
    ("Discovery Museum", "Discovery Museum, Newcastle", "Newcastle (end)",
     "Free science + local-history museum; good for a Newcastle rest day."),
    ("Great North Museum: Hancock", "Great North Museum, Newcastle", "Newcastle (end)",
     "Natural history + a Hadrian's Wall gallery; free."),
    ("Tynemouth beach", "Tynemouth", "Newcastle (end)",
     "Sandy beach at the Tyne mouth; a low-key spare-day trip by Metro or bike."),
]
