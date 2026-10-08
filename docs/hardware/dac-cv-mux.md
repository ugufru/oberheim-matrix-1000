# DAC, CV multiplexing & sample-and-hold

How one DAC feeds every control voltage of all six voices. This is the analog
side of the firmware [voice engine](../firmware/voice-engine.md) (#8). Addresses
and the write protocol are from the **v1.11** ROM. The circuit detail is from the
schematic: Bob Grieb's redrawn set (Rev 1.0, 2015; page 4 "DAC, S&H", page 5
"Voice Circuitry") cross-checked against Oberheim's own sheets (document 2457
Rev B, 1988: sheet 3 "DAC", sheet 11 "Voice 6"). Sheet and part references below
use those drawings.

## The scheme

There is **one system DAC**, an **AM6012** 12-bit DAC (U711), in the `$1000–$13FF`
I/O block. It is **time-multiplexed**: the CPU writes a value, and CD4051
multiplexers steer the DAC output (`ANG`) to one **control input of one voice**.
The firmware cycles through all inputs × voices so each is refreshed before it
droops.

The CEM3396's control inputs are **high-impedance, 0 to +5 V**, so no buffer
amplifiers are needed (the datasheet: "eliminates the usual Sample & Hold Buffers
in a multiplexed DAC system"). The hold is passive. Every CV has a **0.033 µF
hold capacitor** on the mux output, then a **1 MΩ / 0.0068 µF** RC into the CEM3396
pin, which smooths the step on each refresh. So the topology is **DAC → output
amplifier (with range switching) → CD4051 → hold cap → RC → CEM3396 pin**, fanning
one DAC out to 10 CVs × 6 voices.

## How an address becomes a route

The channel address the firmware writes to *is* the routing. On every write to
an **even** address in the block, U709 (74HCT374) latches **address lines**, not
data, into the mux selects (page 4):

| Address bit | Latched as | Meaning |
|---|---|---|
| A1, A2, A3 | `SHA`, `SHB`, `SHC` | mux channel 0–7 (`(addr >> 1) & 7`) |
| A4, A5, A6 | U715 (74HC138) select | which of 8 muxes: `SH1`–`SH6` = voices 1–6, `SH7` = U701, `SH8` = U702 |
| A7 | `RANGE1` | DAC output range switch (see below) |
| A8 | `RANGE2` | DAC output range switch |

The same even-address write clocks the DAC's **high data byte** into U712. An
**odd**-address write clocks the **low byte** into U713. Data bits (page 4):

| Byte | Bit(s) | Goes to |
|---|---|---|
| even (high) | 6–0 | DAC D1 (MSB) … D7 |
| even (high) | 7 | `FASTb` (active low, see [The fast path](#the-fast-path)) |
| odd (low) | 7–3 | DAC D8 … D12 (LSB) |
| odd (low) | 2 | `ENS&Hb`: enables U715, so **0 = mux connected** |

## The write sequence

The per-parameter DAC write is done by **twelve destination primitives at
`$8950`–`$8D1B`** (ten CVs plus two pulse-off variants). Each loads a cached
channel pointer from the voice block and writes the value. E.g. `$8984`:

```
8984  ASLB / ROLA ×2   ; 13-bit value << 2: value bits 12..1 land on D1..D12
8988  ORA <$0B         ; per-voice "fast" flag into bit 7
898D  EORA #$80        ; bit 7 is FASTb, active low
898F  ORB #$04         ; low byte with ENS&Hb = 1 (mux off)
8991  LDX <$79         ; this voice's channel address ($1000 + n*$10)
8993  STB 1,X          ; odd write: low data, mux disconnected
8998  STA ,X+          ; even write: high data + latch the route from the address
899A  ANDB #$FB        ; ENS&Hb = 0
...   STB ,X           ; odd write again: mux connected, DAC drives the hold cap
...   PULU PC          ; next primitive
```

So each CV is: **disconnect, set value and route, connect**. The mux stays
connected until the next primitive's first write disconnects it, so the DAC
charges the hold cap for the whole interval. Most primitives add a short
`PSHS/PULS` delay before connecting, to let the DAC settle. The value is clamped to
`$1FFF` (13 bits) and shifted left two places, so the 12-bit DAC gets value bits
12..1 and bit 0 is overwritten by the `ENS&Hb` strobe.

(Earlier revisions said `EORA #$80` converted a signed value to offset binary.
The schematic shows bit 7 is not a data bit at all: it is `FASTb`. They also
called `STA $1800` at `$8995` a "mux select strobe". `$1800` decodes to `SWb`, the
panel switch *read* buffers (page 1, page 7), and the route is latched from the
address, so that store has no documented effect. It appears only in this one
primitive.)

## Per-voice channel map

The firmware caches every channel address in the voice block at boot
(`vec_RESET`, `$80D8–$8146`), so scan-out is an indexed store, not address
arithmetic. Eight pointers are built as a constant plus `$7207` (which steps by
`$10` per voice); two more, plus the pitch and range-latch addresses, come from
the 18-byte-per-voice **`$8220` boot table**. Voice `n` = 0…5.

Each row is grounded three ways in the code (the **compiler** that emits the
primitive, which stores the matrix destination code in `$7220` and reads the
patch parameter from the active patch at `$7218`; the **primitive** that does the
store; the **pointer** it loads) and then by the schematic route.

The compilers index the active patch (`$7218` = `$7A19`) by **parameter number**:
`+$0A` is param 10, `+$1F` is param 31. The unpacked parameters therefore start
8 bytes into that buffer, consistent with `internal[i] = param i+8` for the unpack
output ([decoding.md](../patch-rom/decoding.md)). The reads only make sense this
way. For example, the DCO2 PW compiler tests bits 0 and 2 of `+$12`, and param 18
is the 3-bit DCO2 noise/wave/pulse enable.

| Dest (`$7220`) | Parameter (patch #) | Compiler | Primitive (store) | Ptr | Channel address | Mux, ch | Range | CEM3396 pin |
|---|---|---|---|---|---|---|---|---|
| 3 | DCO1 waveshape (10) | `$9633` | `$8950` (`$8993`) | `+$79` | `$1000 + n×$10` | voice, 0 | | Wave A (2) |
| 9 | VCF frequency (26) | `$97D7` | `$8C0A` (`$8C70`) | `+$85` | `$1102 + n×$10` | voice, 1 | 2 | Filter freq (20) |
| 11 | VCA1 (31) | `$9907` | `$8CFA` (`$8D02`) | `+$8D` | `$1004 + n×$10` | voice, 2 | | Log gain (1) |
| 2 | DCO1 pulse width (11) | `$9660` | `$89B8` (`$89E0`) | `+$7B` | `$1006 + n×$10` | voice, 3 | | Pulse A (5) |
| 2, off | (DCO1 pulse disabled) | `$9660` | `$89AF` (`$89E0`) | `+$95` | `$1086 + n×$10` | voice, 3 | 1 | Pulse A (5) |
| 12 | VCA2 (envelope) | `$992F` | `$8D1B` (`$8D45`) | `+$8F` | `$1008 + n×$10` | voice, 4 | | Linear gain (22) |
| 5 | DCO2 pulse width (16) | `$9788` | `$8BCC` (`$8BF4`) | `+$83` | `$100A + n×$10` | voice, 5 | | Pulse B (7) |
| 5, off | (DCO2 pulse disabled) | `$9788` | `$8BC3` (`$8BF4`) | `+$97` | `$108A + n×$10` | voice, 5 | 1 | Pulse B (7) |
| 8 | VCF FM amount (30) | `$9846` | `$8C95` (`$8C9D`) | `+$87` | `$108C + n×$10` | voice, 6 | 1 | Filter mod (11) |
| 6 | DCO2 waveshape (15) | `$975B` | `$8B67` (`$8BAA`) | `+$81` | `$100E + n×$10` | voice, 7 | | Wave B (10) |
| 7 | DCO mix (20) | `$98E5` | `$8CD6` (`$8CDE`) | `+$8B` | `$1160 + 2n` | U701, `n` | 2 | Balance (14) |
| 10 | VCF resonance (27) | `$9866` | `$8CB5` (`$8CBD`) | `+$89` | `$106C + 2n` | U701 ch 6–7 (n = 0–1), U702 ch 0–3 (n = 2–5) | | Resonance (15) |

"voice" is that voice's own CD4051 (`UX03` on page 5; U603 on Oberheim's voice 6
sheet), selected by `SH(n+1)`. The shared muxes on page 4 carry `BAL1–6` and
`RES1–2` (U701) and `RES3–6` (U702), exactly the stride-2 addresses above.

The schematic route agrees with the code on every channel where the parameter
alone fixes the pin (waveshape, PW, cutoff, FM, mix, resonance). It also settles
the two questions the code could not:

- **DCO1 = converter A.** Channel 0 and 3 run to Wave A and Pulse A. The
  wave-select table (below) independently agrees.
- **The VCA names are crossed.** The patch's **VCA1** (param 31, velocity by
  default) reaches pin 1, the CEM3396's **log/audio-taper** gain. The patch's
  **VCA2** (the Env 2 loudness destination) reaches pin 22, the **linear** gain.
  Oberheim's own sheet labels the chip pins "VCA1 (LIN)" (22) and "VCA2 (EXP)"
  (1), so chip-level and patch-level names are swapped. Earlier revisions had
  VCA1 = linear.

Pitch (dest 1, DCO1: compiler `$95AB` → `$8765`; dest 4, DCO2: compiler `$96A5`
→ `$89F6`) does not use the DAC; it loads the voice's 8253 counters (`+$75`/`+$91`
for DCO1, `+$7D`/`+$93` for DCO2, from the `$8220` table). See
[voice-architecture.md](voice-architecture.md).

## Output ranges (`RANGE1`, `RANGE2`)

U710 (CD4053) switches resistors into the summing node of the DAC output
amplifier U706, shifting the output window for that write (page 4): `RANGE1`
(A7) switches in a 182 kΩ resistor, `RANGE2` (A8) swaps 133 kΩ (R726) for 20 kΩ
(R724). The firmware uses them per parameter, which matches what the datasheet
asks of each input:

| Range | Used for | Datasheet need |
|---|---|---|
| none | waveshapes, PW, VCAs, resonance | 0 to +5 V |
| `RANGE1` (`+$80`) | **pulse off**, VCF FM amount | pulse off wants Vpw slightly **negative** (−50 to −500 mV); FM amount is ~1% at 0 V |
| `RANGE2` (`+$100`) | VCF frequency, mix | frequency CV spans −2.5 to +5 V; mix is bipolar (≈ −2 to +2 V) |

This resolves the "pulse off writes to PW + `$80`" puzzle: it is the **same mux
channel and pin** as normal PW, written through `RANGE1` so a zero value lands
below 0 V. The `$89AF`/`$8BC3` primitives also wait ~20 loops first, giving the
output amplifier time to swing. The exact voltages of each range were not
computed here.

## The fast path

Each voice has a **second CD4051** (`UX02` on page 5; U602 on Oberheim's sheet)
on the same channel selects, wired to the **pin side** of each 1 MΩ smoothing
resistor. It is enabled only when the voice is selected **and** `FASTb` is low
(an OR gate, `UX04`). So a normal write charges the hold cap and the pin follows
through the RC; a fast write drives the pin directly and the CV **steps
immediately**.

The firmware sets `FASTb` from the per-voice flag `<$0B`, which is ORed into bit
7 before the `EORA #$80`. The modulation source heads set it: `$9D9D` (keyboard
tracking, from voice `+$23`), `$9DB7` (portamento, from `+$25`), and the matrix
source taps from `$9DED` on, which OR in their own flags. Most destination
primitives then clear it. So a destination whose source just **jumped** (a new
note) is written fast, and everything else is slewed.

## What the primitives' arithmetic confirms

The datasheet (application hints, pp. 6–9) says the waveshape CV must scale
**in proportion to frequency** (`Vwf = F·Rt·Ct·5/12·Vcc·α`), that the pulse-width
CV must scale **with the waveshape CV**, and that the timing resistor should be
**range-switched** for a wide pitch range. The code does all three:

- The pitch primitives store a pitch-derived factor in `+$35` from the `$A752`
  table. The waveshape primitives (`$8950`, `$8B67`) clamp the shape to `$3F`,
  floor it at `$1E00`, keep it in `+$37`, and write `+$37 × +$35` (clamped
  `$1FFF`). So **waveshape tracks pitch**.
- The PW primitives (`$89B8`, `$8BCC`) multiply the PW value by that same `+$37`.
  So **PW tracks the waveshape CV**.
- Each pitch primitive compares the note against `$3C80` and keeps a range flag
  (`+$31` DCO1, `+$32` DCO2, `$00` or `$FF`). The waveshape primitive writes that
  flag to **`$1C00 + n`** (DCO1, `+$77`) or **`$1C80 + n`** (DCO2, `+$7F`), ordered
  before or after the DAC write depending on the direction of the switch. The
  per-range pitch offsets are `+$39/+$3B` and `+$3D/+$3F`, defaulted at `$DD88`.

The schematic confirms those latches (Oberheim sheet 3). `$1C00` (`L1`) and
`$1C80` (`L2`) are **74HC259 addressable latches** (U703, U704): `A0–A2` pick the
output and `BD0` is the data, so `$1C00 + n` sets one bit. U703's outputs are
`RA1–RA6` and U704's are `RB1–RB6`, the per-voice transistors that switch each
converter's timing resistor (page 5: `RAX`/`RBX` turn on `QX02`/`QX04`, which put
36 kΩ in parallel with the 510 kΩ `R_T` for the high range, the datasheet's
recommended method). U703's Q6 is `NOI`, the global **noise** enable, so `$1C06` is the
noise switch, not an LED latch.

## Wave select, sync and mute: global, at `$1D00`

The CEM3396's eleventh input, **wave select** (pin 6), is not on the DAC. Every
voice's pin 6 is wired to one shared `WAVE` line, driven the way the datasheet's
Figure 2 suggests: two logic bits into a transistor and resistor network
(Oberheim sheet 3: Q701, R716 82 kΩ, R717 43 kΩ, to −5 V). Those bits come from
`$1D00` (`L3`), a 74HC174 (U705) that also carries the other global voice
controls:

| `$1D00` bit | U705 output |
|---|---|
| 0 | Q3 (unlabelled) |
| 1 | `MUTE` |
| 2 | `SYNC2` |
| 3 | `SYNC1` |
| 4, 5 | `WAVE` network |

The firmware builds this byte at `$9529`–`$9587` from the patch and keeps a shadow
in `$7235`. The two sloped-wave enables (bit 1 of param 13, bit 1 of param 18)
index the table at **`$9594`**: `$20` (neither), `$30` (DCO1 only), `$10` (DCO2
only), `$00` (both). In order of voltage those are the datasheet's four levels
(both on, B only, none, A only), so `$30` = "A only" for DCO1 is a second
confirmation that DCO1 is converter A. DCO sync (param 25) goes into bits 2–3;
bits 0–1 are kept from the shadow. Boot clears bit 1 (`$81D7`) after
initialising, which releases `MUTE`.

Because these lines are shared, **wave selection, sync and noise are per patch,
not per voice**: all six voices always have the same sloped-wave enables, sync
mode and noise state. Everything else is per voice.

`$107E`, which an earlier revision proposed as the wave-select path, decodes to
channel 7 of U702, which is unconnected on both schematics. The firmware writes
`$7213`/`$7214` there with a single even-address store (`$9600`, `$9728`), which
re-latches the route without the connect strobe. Its purpose is still unknown;
it does not drive wave select.

## Per-voice calibration tables (cutoff and resonance)

Cutoff and resonance are the two channels the firmware **corrects per voice**:

- **VCF frequency** (`$8C0A`) interpolates the value through a table at
  **voice `+$2AA`** (pointer `+$73`, set at `$80C8`). Defaults at `$DD49–$DD84`
  are nine points from `$0B19` down to `$04D9` in steps of `$C8`. The calibration
  routine at `$B23F` rewrites them.
- **Resonance** (`$9866`, at compile time) folds a per-voice correction word at
  **voice `+$2A8`** (cleared at `$DDAE`) into the value. A resonance of 63 bypasses
  the correction and writes full scale `$7FFF`.

This is the "filter/VCF calibration" side of CALIBRATE (autotune-selftest.md):
the oscillators need no tuning, but the analog filter does.

## The boot write mutes the voices

`FUN_81e4` writes raw `$8000` to `$1008 + n×$10` for all six voices, repeating 50
times (`$7222 = $32`). With bit 7 = `FASTb` high (normal path) and data 0, that is
**VCA2 = 0** on every voice, so all output VCAs start closed. (An earlier revision
called it a "mid-scale settle".)

## Correction: `FUN_8765` is the *timer* write, not the DAC

An earlier revision documented a "DAC write protocol" using `FUN_8765`, writing
two bytes to the **same** address then toggling `+$91`. That is the **8253 pitch
write**: writing LSB-then-MSB to one address is the 8253 counter load, `+$75`/`+$91`
are the voice's timer counter/control (from the `$8220` table), and it is driven
by the `$A652` note→divider table (voice-architecture.md / timing-clocks.md).

The `$8220` table caches **both** kinds of target per voice: the two 8253
counters (`$0000` region, pitch) *and* DAC channels (`$106x`/`$116x`), alongside
the `$1C00`/`$1C80` range-latch addresses.

## Failure points

The DAC, the **4053** next to it, and the pair of **4051s** behind each voice are
the classic field failures (one stuck or wandering parameter or voice). The
CEM3396s themselves are usually fine. (Community/service literature.) With the
map above, a symptom can be traced to its part: a whole voice wrong points at
that voice's `UX03`; one parameter wrong on every voice points at the DAC
output stage or U710 range switch (if it is a ranged parameter); resonance or mix
wrong on some voices points at U701/U702.

## Open items

- Compute the actual output voltage window for each `RANGE` setting from the U706
  resistor network.
- Explain the `$107E` write and the `STA $1800` in `$8991`.
- Confirm the AM6012 part marking on a real board.
- Resolve the `$2018+` voice-status lines (see voice-architecture.md, #31).
