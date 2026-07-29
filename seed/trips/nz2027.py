"""New Zealand 2027 seed data. Transcribed once from the markdown plans in
../new_zealand_2027/ (itinerary_draft.md authoritative). Consumed by seed_trip.py.

Tuple formats (shared by every trip module):
  LEGS:  (seq, name, place_key, location, start, end, accom, status, ref, notes)
  COSTS: (label, amount, currency, kind, category, leg_key or None)
  TASKS: (title, leg_key or None)
  IDEAS: (title, place_key or None, leg_key, notes)
place_key is looked up in seed/places.py for lat/lon; leg_key matches a leg name.
"""

TRIP = {
    "name": "New Zealand 2027",
    "start_date": "2027-02-08",   # AMS departure; Singapore stopover Feb 8-10
    "end_date": "2027-03-20",     # AKL -> AMS departure day
    "currency": "NZD",
    "fx_to_eur": 0.56,
    "budget_eur": 18000,
}

# Legs: the 38-night dated chain from itinerary_draft.md (authoritative).
# Picton ferry is folded into the Wellington leg (not its own stop).
LEGS = [
    (1, "Christchurch", "Christchurch", "Christchurch, New Zealand",
     "2027-02-10", "2027-02-13", None, "tbd", None,
     "Arrival recovery; car pickup Feb 13. Margaret Mahy playground & Botanic Gardens."),
    (2, "Twizel (high country)", "Twizel", "Twizel, New Zealand",
     "2027-02-13", "2027-02-17", "Mountain Chalets Motel (2-BR + kitchenette)",
     "booked", None,
     "Booked EUR122/nt x4, free cancellation. Day-trip Tekapo (45min) + Mt Cook Hooker Valley (50min). High country consolidated to one base."),
    (3, "Dunedin / Otago Peninsula", "Dunedin", "Dunedin, New Zealand",
     "2027-02-17", "2027-02-19", None, "tbd", None,
     "Wildlife leg: Royal Albatross Centre, penguins (daytime hides), sea lions. Twizel->Dunedin ~3h. Favour daytime (penguins ashore ~9pm is late for a 4yo)."),
    (4, "Te Anau", "Te Anau", "Te Anau, New Zealand",
     "2027-02-19", "2027-02-22", "TOP 10 studio (kitchen)", "booked", "#180797",
     "Booked NZ$695/3nt park-direct. Deposit NZ$245 paid; balance NZ$450 due at check-in. Fiordland/Milford gateway."),
    (5, "Queenstown", "Queenstown", "Queenstown, New Zealand",
     "2027-02-22", "2027-02-24", None, "tbd", None,
     "Hub; TOP 10 park-direct. Skyline Gondola + Luge, lakefront. Trimmed 3->2 to fund Dunedin."),
    (6, "Wanaka", "Wanaka", "Wanaka, New Zealand",
     "2027-02-24", "2027-02-26", None, "tbd", None,
     "Retreat: lakeside bach. Puzzling World, lakefront playground. Trimmed 3->2 to fund Dunedin."),
    (7, "West Coast (Haast/Fox)", "Haast", "Haast, New Zealand",
     "2027-02-26", "2027-02-27", None, "tbd", None,
     "Haast Pass waterfall walks off the road. One-night stopover."),
    (8, "Franz Josef", "Franz Josef", "Franz Josef Glacier, New Zealand",
     "2027-02-27", "2027-03-02", None, "tbd", None,
     "Hub; TOP 10. Glacier; West Coast Wildlife Centre (kiwis)."),
    (9, "Punakaiki", "Punakaiki", "Punakaiki, New Zealand",
     "2027-03-02", "2027-03-04", "Beach Camp family double (shared bath)",
     "booked", "#5738926961",
     "Booked EUR111/2nt via Booking.com, free cancel to end-Feb. Pancake Rocks & blowholes."),
    (10, "Abel Tasman (Bark Bay)", "Bark Bay", "Bark Bay, Abel Tasman, New Zealand",
     "2027-03-04", "2027-03-06", "DOC Bark Bay Great Walk tent site (own tent)",
     "booked", "DOC #6414243",
     "Booked NZ$154/2nt. Boat-access; water taxi (Aqua Taxi ~NZ$248 return) still to book, drop Mar 4 am + pickup 12:45 Mar 6. Marahau parks sold out -> camping pivot."),
    (11, "Nelson (recovery)", "Nelson", "Nelson, New Zealand",
     "2027-03-06", "2027-03-07", None, "tbd", None,
     "Break camp + water-taxi pickup Mar 6, ~1h drive. Real bed/laundry/resupply after 2 nights camping; splits the Picton drive."),
    (12, "Wellington", "Wellington", "Wellington, New Zealand",
     "2027-03-07", "2027-03-09", None, "tbd", None,
     "Drive Nelson->Picton (~2h) + Cook Strait ferry Mar 7 (Interislander 2:15PM Picton->Wgtn, TOP 10 10% applies). Te Papa Museum (kids' Discovery Centres)."),
    (13, "Taupo", "Taupo", "Taupo, New Zealand",
     "2027-03-09", "2027-03-11", None, "tbd", None,
     "Hub; TOP 10 (best facilities). Hot-water streams, Huka Falls, geothermal pools. Trimmed 3->2 to fund Nelson."),
    (14, "Rotorua", "Rotorua", "Rotorua, New Zealand",
     "2027-03-11", "2027-03-13", None, "tbd", None,
     "Family Holiday Park or bach (skip the ex-TOP 10). Te Puia geysers, mud pools, Agrodome."),
    (15, "TBD (2 nights to reallocate)", None, None,
     "2027-03-13", "2027-03-15", None, "tbd", None,
     "Hobbiton/Matamata scrapped (not interested). These 2 nights need reallocating: candidates Coromandel (3->5), Auckland (2->4), or restore Taupo (2->3). Dates held so the chain stays 38 nights."),
    (16, "Coromandel", "Hot Water Beach", "Hot Water Beach, New Zealand",
     "2027-03-15", "2027-03-18", None, "tbd", None,
     "Hot Water Beach TOP 10 or quiet bach (TBD). Dig-your-own spa; Cathedral Cove."),
    (17, "Auckland", "Auckland", "Auckland, New Zealand",
     "2027-03-18", "2027-03-20", None, "tbd", None,
     "Final nights; Sky Tower or Mission Bay. Fly out Mar 20."),
]

# Remaining (not-yet-booked) accommodation: ~NZ$8,000 total estimate minus the
# booked lines (695 + 154 NZD, plus 488 + 111 EUR converted back to NZD).
FX = TRIP["fx_to_eur"]
_REMAINING_ACCOM = round(8000 - 695 - 154 - (488 + 111) / FX, -2)

COSTS = [
    ("Car hire — SNAP Mitsubishi ASX (incl. Full Protection)", 1815, "EUR",
     "booked", "transport", None),
    ("Flights AMS<->CHC/AKL via SIN, 3 pax (not yet booked)", 5427, "EUR",
     "estimated", "transport", None),
    ("Fuel & RUC (~3,500 km diesel)", 1650, "NZD", "estimated", "transport", None),
    ("Cook Strait ferry (car + 2 adults + child)", 400, "NZD",
     "estimated", "transport", None),
    ("TOP 10 Holiday Parks membership (2 yr)", 55, "NZD", "booked", "other", None),
    ("Mountain Chalets Motel, EUR122/nt x4", 488, "EUR", "booked",
     "accommodation", "Twizel (high country)"),
    ("TOP 10 studio, NZ$695/3nt (#180797)", 695, "NZD", "booked",
     "accommodation", "Te Anau"),
    ("Beach Camp family double, EUR111/2nt (#5738926961)", 111, "EUR", "booked",
     "accommodation", "Punakaiki"),
    ("DOC Bark Bay tent site, NZ$154/2nt (DOC #6414243)", 154, "NZD", "booked",
     "accommodation", "Abel Tasman (Bark Bay)"),
    ("Remaining accommodation (units/baches, ~30 nights)", _REMAINING_ACCOM,
     "NZD", "estimated", "accommodation", None),
    ("Food & groceries", 3000, "NZD", "estimated", "food", None),
    ("Activities (cruise, gondolas, wildlife tours)", 4000, "NZD",
     "estimated", "activities", None),
]

TASKS = [
    ("Book flights (option EUR 5,427 via SIN, non-refundable)", None),
    ("Discuss 6-week leave with employer", None),
    ("Apply for NZeTA (Electronic Travel Authority)", None),
    ("Check passport expiry dates for 2027", None),
    ("Book Christchurch stay, 3 nights Feb 10-13", "Christchurch"),
    ("Reserve child seat with SNAP (pre-book, peak Feb scarcity)", "Christchurch"),
    ("Add second driver at the desk ($3/day)", "Christchurch"),
    ("Confirm one-way fee at the desk (no extra beyond quote)", "Christchurch"),
    ("Book Cook Strait ferry (Interislander ~NZ$346-430; TOP 10 10% applies)",
     "Wellington"),
    ("Book Abel Tasman water taxi (Aqua Taxi NZ$248 return, pickup 12:45 Mar 6)",
     "Abel Tasman (Bark Bay)"),
    ("Decide the TBD 2-night reallocation (Coromandel / Auckland / Taupo)",
     "TBD (2 nights to reallocate)"),
]

IDEAS = [
    ("Hooker Valley Track", "Hooker Valley Track", "Twizel (high country)",
     "Flat, stroller-friendly; swing bridges + glacier lake at Mt Cook (~50 min)."),
    ("Aoraki/Mt Cook — Tasman Glacier & Alpine Centre", "Aoraki/Mt Cook",
     "Twizel (high country)",
     "Tasman Glacier terminal-lake boat; Sir Edmund Hillary Alpine Centre (rainy-day/kid option); Kea Point."),
    ("Lake Tekapo — Church of the Good Shepherd", "Lake Tekapo",
     "Twizel (high country)", "Turquoise water, iconic church (~45 min from Twizel)."),
    ("Tekapo stargazing (Dark Sky reserve)", "Mt John Observatory",
     "Twizel (high country)", "Mt John / Dark Sky. Late night — weigh against a 4yo's bedtime."),
    ("Royal Albatross Centre (Taiaroa Head)", "Royal Albatross Centre",
     "Dunedin / Otago Peninsula",
     "Only mainland royal albatross colony; daytime tours, toddler-friendly."),
    ("Penguin Place (daytime hides)", "Penguin Place", "Dunedin / Otago Peninsula",
     "Yellow-eyed + little blue penguins; daytime hides beat the dusk colony for a 4yo."),
    ("Milford Sound cruise", "Milford Sound", "Te Anau",
     "Iconic fiord day-trip/cruise from Te Anau (~2h each way)."),
    ("Te Anau glow-worm caves", "Te Anau glow-worm caves", "Te Anau",
     "Boat + cave walk; free bird sanctuary nearby (rare Takahe)."),
    ("Skyline Gondola + Luge", "Skyline Gondola", "Queenstown",
     "Kids love the luge 'bubbles'; lakefront views."),
    ("Puzzling World", "Puzzling World", "Wanaka",
     "Optical illusions; good for all ages. Lakefront playground nearby."),
    ("Haast Pass waterfall walks", "Haast Pass waterfalls", "West Coast (Haast/Fox)",
     "Short 5-min waterfall walks right off the road (e.g. Fantail Falls)."),
    ("Franz Josef Glacier", "Franz Josef Glacier", "Franz Josef",
     "Valley walk to the glacier face; guided options."),
    ("West Coast Wildlife Centre (kiwis)", "West Coast Wildlife Centre",
     "Franz Josef", "See kiwis; good rainy-day option."),
    ("Pancake Rocks & blowholes", "Pancake Rocks", "Punakaiki",
     "Dolomite Point boardwalk; blowholes best near high tide."),
    ("Te Papa Museum", "Te Papa", "Wellington",
     "Interactive kids' Discovery Centres; free entry."),
    ("Huka Falls", "Huka Falls", "Taupo",
     "Powerful falls; short walk. Hot-water streams to soak in nearby."),
    ("Te Puia geysers & mud pools", None, "Rotorua",
     "Pohutu geyser, bubbling mud; Maori cultural centre."),
    ("Agrodome sheep show", None, "Rotorua", "Farm show; kid-friendly."),
    ("Hot Water Beach — dig your own spa", "Hot Water Beach", "Coromandel",
     "Dig a hot pool in the sand around low tide; bring a spade."),
    ("Cathedral Cove", None, "Coromandel",
     "Iconic sea arch; walk-in (check access) or kayak/boat."),
    ("Sky Tower / Mission Bay", None, "Auckland",
     "City view from Sky Tower or a last beach afternoon at Mission Bay before flying home."),
]
