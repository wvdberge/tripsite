"""Static place-name -> (lat, lon) lookup. Approximate coordinates, hand-set.
No geocoding API (the box is LAN-only). Used by import_data.py to place legs
and ideas on the map. Keys are the canonical names the importer passes in.
"""

PLACES = {
    # --- Legs (bases along the route) ---
    "Christchurch": (-43.5321, 172.6362),
    "Twizel": (-44.2569, 170.0965),
    "Dunedin": (-45.8788, 170.5028),
    "Te Anau": (-45.4144, 167.7180),
    "Queenstown": (-45.0312, 168.6626),
    "Wanaka": (-44.7032, 169.1321),
    "Haast": (-43.8811, 169.0420),
    "Franz Josef": (-43.3892, 170.1836),
    "Punakaiki": (-42.1150, 171.3360),
    "Bark Bay": (-40.9167, 173.0333),
    "Nelson": (-41.2706, 173.2840),
    "Wellington": (-41.2865, 174.7762),
    "Taupo": (-38.6857, 176.0702),
    "Rotorua": (-38.1368, 176.2497),
    "Hot Water Beach": (-36.8886, 175.8078),
    "Auckland": (-36.8485, 174.7633),
    # (TBD leg intentionally has no coordinates)

    # --- Idea highlights ---
    "Lake Tekapo": (-44.0027, 170.4795),
    "Mt John Observatory": (-43.9866, 170.4650),
    "Hooker Valley Track": (-43.7226, 170.0989),
    "Aoraki/Mt Cook": (-43.7340, 170.0940),
    "Royal Albatross Centre": (-45.7717, 170.7275),
    "Penguin Place": (-45.7897, 170.7003),
    "Milford Sound": (-44.6414, 167.8974),
    "Te Anau glow-worm caves": (-45.4150, 167.7050),
    "Skyline Gondola": (-45.0244, 168.6510),
    "Puzzling World": (-44.6970, 169.1650),
    "Haast Pass waterfalls": (-44.0940, 169.3540),
    "Franz Josef Glacier": (-43.4667, 170.1833),
    "West Coast Wildlife Centre": (-43.3897, 170.1810),
    "Pancake Rocks": (-42.1147, 171.3260),
    "Te Papa": (-41.2905, 174.7820),
    "Huka Falls": (-38.6489, 176.0900),
}


def coords(name):
    """Return (lat, lon) or (None, None) if the place is unknown."""
    return PLACES.get(name, (None, None))
