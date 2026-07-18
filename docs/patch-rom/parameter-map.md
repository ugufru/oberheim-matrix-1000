# Patch parameter map (the 134-parameter model)

The canonical Matrix-6/Matrix-1000 patch is **134 parameters** (numbered 0–133).
This numbering is the addressing used by the SysEx single-patch dump and by
NRPN/quick-edit, and it is the *meaning* layer that the packed 80-byte record
(#15) expands into. The table below is the documented Matrix-6/1000 layout
(sources: CMU `m6-patch`, youngmonkey Matrix-1000 SysEx), annotated where the
firmware analysis independently confirms an entry.

> Two views, don't confuse them: this is the **parameter-number / SysEx** view.
> The firmware's *internal* working buffer (the unpack output, #15) holds the
> same information but its byte ordering is the firmware's own; correlating
> internal offsets ↔ parameter numbers is finished in #17.

## Global / name

| # | Parameter | Bits | Notes |
|---|---|---|---|
| 0–7 | **Patch name** | 6 ea | 8 chars × 6-bit — matches the packed name at record `$24` (#15) |
| 8 | **Keyboard mode** | 2 | Reassign / Rotate / Unison / Rob — **firmware-confirmed**: read at `$7A19+8` for unison/voice-assign (#11, `FUN_d348`) |

## DCO1 / DCO2

| # | Parameter | Bits | Range |
|---|---|---|---|
| 9 | DCO1 frequency | 6 | 0–63 |
| 10 | DCO1 saw shape | 6 | 0–63 |
| 11 | DCO1 pulse width | 6 | 0–63 |
| 12 | DCO1 freq mod select | 2 | vibrato/bend |
| 13 | DCO1 waveform enable | 2 | wave/pulse |
| 14 | DCO2 frequency | 6 | 0–63 |
| 15 | DCO2 saw shape | 6 | 0–63 |
| 16 | DCO2 pulse width | 6 | 0–63 |
| 17 | DCO2 freq mod select | 2 | vibrato/bend |
| 18 | DCO2 waveform enable | 3 | noise/wave/pulse |
| 19 | DCO2 detune | 6 ± | −32…+31 |
| 20 | (DCO mix / portamento-related) | — | |
| 21 | DCO1 keyboard/porta | 2 | |
| 22 | DCO1 click | 1 | |
| 23 | DCO2 keyboard/porta | 2 | |
| 24 | DCO2 click | 1 | |
| 25 | DCO sync mode | 2 | |

## VCF / VCA

| # | Parameter | Bits | Range |
|---|---|---|---|
| 26 | VCF frequency | 7 | 0–127 |
| 27 | VCF resonance (Q) | 6 | 0–63 |
| 28 | VCF freq mod select | 2 | vibrato/bend |
| 29 | VCF keyboard/porta | 2 | |
| 30 | VCF FM amount | 6 | 0–63 |
| 31 | VCA1 level | 6 | 0–63 |

## Portamento

| # | Parameter | Bits | Range |
|---|---|---|---|
| 32 | Portamento rate | 6 | 0–63 |
| 33 | Portamento mode | 2 | speed/time/exp1/exp2 |
| 34 | Legato | 1 | on/off |

## LFO1 (35–41) / LFO2 (42–48)

Each LFO: speed, trigger, lag, waveform, retrigger, sample source, amplitude.

| # (LFO1 / LFO2) | Parameter | Bits |
|---|---|---|
| 35 / 42 | Speed | 6 |
| 36 / 43 | Trigger | 2 (none/single/multi/extern) |
| 37 / 44 | Lag | 1 |
| 38 / 45 | Waveform | 3 (tri/up/dn/sqr/rnd/noise/S&H) |
| 39 / 46 | Retrigger point | 5 |
| 40 / 47 | Sample source | 5 |
| 41 / 48 | Amplitude | 6 |

## Envelopes — ENV1 (49–57), ENV2 (58–66), ENV3 (67–75)

Each DADSR envelope shares this layout (offset from the env's base):

| +off | Parameter | Bits |
|---|---|---|
| +0 | Trigger mode | 3 |
| +1 | Delay | 6 |
| +2 | Attack | 6 |
| +3 | Decay | 6 |
| +4 | Sustain | 6 |
| +5 | Release | 6 |
| +6 | Amplitude | 6 |
| +7 | LFO-trigger / gated | 2 |
| +8 | Mode (free-run/DADR) | 2 |

So ENV1 delay = 50, attack = 51, …; ENV2 base 58; ENV3 base 67.

## Tracking generator (76–81) & Ramps (82–85)

| # | Parameter | Bits |
|---|---|---|
| 76 | Tracking source | 5 |
| 77–81 | Tracking points 1–5 | 6 ea |
| 82 | Ramp1 rate | 6 |
| 83 | Ramp1 mode | 2 (Strig/Mtrig/Xtrig/Xgate) |
| 84 | Ramp2 rate | 6 |
| 85 | Ramp2 mode | 2 |

## Fixed / dedicated modulation slots (86–103)

These are the hard-wired front-panel mod routings (signed amount, −64…+63),
distinct from the programmable matrix below. These are exactly the dedicated
taps the per-destination compilers emit in #9.

| # | Routing |
|---|---|
| 86 | DCO1 freq by LFO1 |
| 87 | DCO1 PW by LFO2 |
| 88 | DCO2 freq by LFO1 |
| 89 | DCO2 PW by LFO2 |
| 90 | VCF freq by ENV1 |
| 91 | VCF freq by pressure |
| 92 | VCA1 by velocity |
| 93 | VCA2 by ENV2 |
| 94 | ENV1 amplitude by velocity |
| 95 | ENV2 amplitude by velocity |
| 96 | ENV3 amplitude by velocity |
| 97 | LFO1 amplitude by ramp1 |
| 98 | LFO2 amplitude by ramp2 |
| 99 | Portamento rate by velocity |
| 100 | VCF FM by ENV3 |
| 101 | VCF FM by pressure |
| 102 | LFO1 speed by pressure |
| 103 | LFO2 speed by keyboard |

## Programmable modulation matrix (104–133)

Ten buses, 3 bytes each — **source, signed amount, destination** — the 20-slot
"Matrix Modulation". These are the routings #9's element routines read and compile
into the per-voice program.

| # | Field |
|---|---|
| 104 + 3·n | MODn source (5 bits, 0–31) |
| 105 + 3·n | MODn amount (7 bits signed, −64…+63) |
| 106 + 3·n | MODn destination (5 bits, 0–32) |

for n = 0…9 → bytes 104–133.

## Notes

- **Total: 134 parameters (0–133).**
- The signed mod amounts (86–133) are stored offset; the firmware treats them as
  two's-complement around 0.
- Source/destination code lists (which number = which source/destination) are a
  separate enumeration to be tabulated in #17 alongside the decoder, and tie back
  to the `$Axxx` primitive library in #9.

## Open items

- Tabulate the source and destination code enumerations (which mod number = which
  source / destination) to make the matrix buses fully human-readable (#17/#18).

(The internal working-buffer offset mapping is resolved in #17:
`internal[i] = parameter i+8`; the M1000 does not store the name, params 0–7.)
