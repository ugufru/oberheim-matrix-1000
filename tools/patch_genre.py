"""Heuristic genre/voicing classification of patches from their names.

Names are terse 8-char patchbook names, so this is fuzzy substring matching with a
priority order (first match wins). Returns a genre label used for colouring the
patch map. Purely nominal — the axes (brightness/register) come from the decoded
parameters, not from names.
"""

# (genre, [substrings]) in priority order; first hit wins.
RULES = [
    ("OB-Xa",      ["obxa", "obx", "obca", "obxj"]),
    ("Vintage synth", ["prophet", "cs-80", "cs80", "mini", "moog", "mooog", "arp",
                       "jupit", "juno", "dx", "matrix", "zeta", "synth", "syn ", "synbox",
                       "analog", "sync", "saw", "pulse", "vco"]),
    ("Organ",      ["organ", "orgn", "b3", "lslie", "leslie", "hammon", "pipe", "church",
                    "gospel", "drawb"]),
    ("E-piano/keys", ["piano", "pian", "pno", "papano", "road", "rhode", "wurl", "clav",
                      "elec", "grand", "honky", "tine", "harpsi"]),
    ("Strings",    ["string", "strg", "strng", "viol", "cello", "orch", "ensemb", "arco",
                    "12\"git"]),
    ("Brass/horns", ["brass", "brz", "horn", "trump", "tromb", "tuba", "sax", "flugel",
                     "fanfar"]),
    ("Bass",       ["bass", "fzbass", "wipbass", "fmbass", "fm bass", "fazbas", "fweep"]),
    ("Vocal/choir", ["choir", "voice", "vox", "vocal", "aah", "ooh", "chant"]),
    ("Bells/mallets", ["chime", "bell", "glass", "vibe", "tubular", "celest", "marimb",
                       "xylo", "mallet", "gong", "metal"]),
    ("Pad",        ["pad", "warm", "sweep", "swep", "soft", "air", "ether", "ambien", "drone"]),
    ("Lead",       ["lead", "solo", "ld", "leed"]),
    ("Percussion", ["drum", "dmach", "slap", "gallop", "perc", "tom", "snare", "kick",
                    "clap", "trak", "hit"]),
    ("Plucked/guitar", ["guitar", "gitar", "git", "gtr", "pluck", "harp", "sitar",
                        "banjo", "koto", "pik", "12str"]),
    ("FX/texture", ["fx", "noise", "space", "fire", "wind", "rain", "thunder", "laser",
                    "effect", "echo", "drama", "scape", "weird", "haunt"]),
    ("Woodwind",   ["flute", "pan", "recorder", "oboe", "clarin", "whistl"]),
]

# colour per genre for the map
COLORS = {
    "OB-Xa": "#e74c3c", "Vintage synth": "#e67e22", "Organ": "#8e44ad",
    "E-piano/keys": "#2980b9", "Strings": "#16a085", "Brass/horns": "#d4ac0d",
    "Bass": "#7f5539", "Vocal/choir": "#c0399b", "Bells/mallets": "#27ae60",
    "Pad": "#5dade2", "Lead": "#e84393", "Percussion": "#566573",
    "Plucked/guitar": "#a04000", "FX/texture": "#1abc9c", "Woodwind": "#af7ac5",
    "Other": "#bbbbbb",
}


def genre(name):
    n = name.lower()
    for g, subs in RULES:
        for s in subs:
            if s in n:
                return g
    return "Other"
