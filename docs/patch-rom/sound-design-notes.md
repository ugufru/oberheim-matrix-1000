# Sound-design notes from the factory patches

What the factory programmers actually did, mined from decoding all of the patch
ROM (#15–#17). Reproduce with:

```sh
PYTHONPATH=tools python3 tools/analyze_patches.py \
    reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN \
    reference/extracted/matrix-1000/patch-rom/M1000-PatchROM_27512_C2DB.BIN
```

Dataset: **819 records, 818 non-empty**. Core synthesis parameters
(DCO/VCF/VCA/envelopes/LFOs) are byte-exact (pass-1 unpack). The **matrix-routing
figures are indicative** — those bytes are refined by the firmware's pass-2
(`$E08B`), which the decoder doesn't yet emulate, so treat the routing tallies as
strong trends, not exact counts.

## Voice allocation

| Mode | Patches |
|---|---|
| Reassign | 562 |
| Rotate | 172 |
| Reassign-with-rob | 43 |
| **Unison** | 41 |

Reassign dominates (~69%); only ~5% are unison/mono — as expected for a 6-voice
poly aimed at pads and keys.

## Oscillators

- **DCO sync** is used in **269 / 818 (~33%)** of patches — a third lean on the
  classic sync timbre.

## Filter — dark by default, opened by modulation

- Mean base **cutoff ≈ 15 / 127**; **~74%** of patches sit at cutoff `0–15`, only
  ~6% park it wide open (`80–127`).
- But **VCF Frequency is the #2 modulation destination** (below). The pattern is
  unmistakable: set a **low static cutoff and open it dynamically** with an
  envelope / key-track / pressure — rather than a static bright filter.
- **Resonance**: ~49% use little/none (`0–5`), ~24% push it high (`32–63`); mean
  ≈ 18 / 63. Resonance is a deliberate accent, not a default.

## Envelopes

- **41%** of patches have an ENV1 attack ≤ 2 — i.e. percussive/plucked onsets are
  the single largest envelope archetype.
- ENV1 means A/D/S/R ≈ **14 / 24 / 16 / 23**: moderate everything, with decay and
  release the longest stages (bodies that bloom and tail off).

## Modulation matrix — how the "Matrix" is actually used

- **~3.6 active buses per patch** (of 10 available); only **29** patches use the
  matrix not at all. The programmers genuinely leaned on it.
- **Top destinations**: **DCO1 Frequency** and **VCF Frequency** dominate, then
  envelope times (Env1 Decay), LFO2 Amp, VCA2.
- **Top sources**: **Pressure (aftertouch)** is the most-wired source by a wide
  margin, then Keyboard, LFO1, Pedal 2, LFO2, Velocity.
- Characteristic routings that recur across the bank:
  - **Keyboard / Tracking-Gen → VCF Frequency** (filter key-tracking),
  - **LFO1 → VCF Frequency** (filter wobble/growl),
  - **Pressure → VCA / LFO1 Amp / DCO Wave** (expressive aftertouch),
  - **Keyboard → DCO1 Frequency** and pitch/PW modulation.

The headline: the factory voicing philosophy is **expressive and dynamic** — a
dark filter brought to life by envelopes and a heavy reliance on **aftertouch**
and **key-tracking** through the modulation matrix, rather than static bright
patches.

## Named examples

The patch names come from the Don Solaris patchbook (the M1000 stores none of its
own); paired with the decode by number, the extremes are sonically on-the-nose:

- **Highest resonance:** `#255 chime 1` (resonance 63 — a chime wants a ringing
  filter).
- **Most modulation:** `#201 obxa-12` uses **all 10** matrix buses.
- **Percussive archetype:** `obxa-d5`, `anaxylo*`, `arcangel`, `argex-1` (fast
  attack, long decay).

## The patch map

[`../diagrams/patch-map.svg`](../diagrams/patch-map.svg) plots all 813 non-empty
factory patches in a brightness × register space, coloured by genre. Position is
from the **decoded parameters** (x = static cutoff + envelope filter-opening +
resonance ring; y = oscillator register), rank-scaled and force-relaxed so the
cloud is readable; colour is the heuristic genre from the name.

What it shows:

- a dense **bright + low-register** cluster (bottom-right): **bass, OB-Xa, brass**
  — the punchy "money" sounds;
- **strings / organ / brass** spread across the **high register** (top);
- **leads, pads, vocal, FX** in the **mellow** left;
- a comparatively sparse mid-zone — factory patches tend toward the extremes
  rather than the middle.

By name, the identifiable genres are led by **Bass, Strings, vintage-synth,
Brass, OB-Xa emulations and E-pianos** — a classic imitative bread-and-butter
library, with a long tail of abstract/experimental names. (Build the map with
`tools/patch_map_svg.py`; genre rules in `tools/patch_genre.py`.)

## Caveats / next

- Matrix routing counts are indicative pending pass-2 (`$E08B`) emulation; some
  invalid source codes (21–31) appear as artifacts and are ignored above.
- A per-patch **named, labelled** dump is in `build/patches.csv` (regenerable via
  `tools/decode_patches.py`) for anyone who wants to slice the data differently.
