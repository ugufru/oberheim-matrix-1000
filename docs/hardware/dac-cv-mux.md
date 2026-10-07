# DAC, CV multiplexing & sample-and-hold

How one DAC feeds every control voltage of all six voices. This is the analog
side of the firmware [voice engine](../firmware/voice-engine.md) (#8). Addresses
and the write protocol below are from the **v1.11** ROM; the analog detail is the
schematic's authority (Bob Grieb redrawn set; `bit-hack`).

## The scheme

There is **one system DAC** (an Analog Devices **AM6012**, 12-bit, per the
schematic notes) in the `$1000–$13FF` I/O block. It is **time-multiplexed**: the
CPU writes a value and steers it through **CD4051/4053** analog multiplexers to
one specific **control input of one specific voice**. The firmware cycles through
all inputs × voices continuously so each is refreshed before it droops.

Each CEM3396 has **11 separate control inputs** (not one multiplexed input). The
key design point, from the datasheet: those inputs are **high-impedance, 0 to +5 V,
for "direct interface to a CMOS multiplexer from the system DAC" — a feature that
"eliminates the usual Sample & Hold Buffers in a multiplexed DAC system."** In
other words there are **no dedicated per-parameter S&H buffer chips**: the mux
output drives the high-Z pin directly, and the pin's own input capacitance holds
the value between refresh passes. So the topology is **DAC → 4051/4053 mux tree
(selects voice + input) → CEM3396 high-Z pin (self-holding)**, fanning one DAC out
to 11 CVs × 6 voices.

## Per-voice channel map

The firmware caches every channel address in the voice block at boot
(`vec_RESET`, `$80D8–$8146`), so scan-out is an indexed store, not address
arithmetic. Eight pointers are built as a constant plus `$7207` (which steps by
`$10` per voice); two more, plus the pitch and range-latch addresses, come from
the 18-byte-per-voice **`$8220` boot table**. Voice `n` = 0…5.

Each row below is grounded three ways: the **compiler** that emits the primitive
(it stores the matrix destination code in `$7220` and reads the named patch
parameter from the active patch at `$7218`), the **primitive** that does the
store, and the **pointer** it loads.

The compilers index the active patch (`$7218` = `$7A19`) by **parameter number**:
`+$0A` is param 10, `+$1F` is param 31. The unpacked parameters therefore start
8 bytes into that buffer, consistent with `internal[i] = param i+8` for the unpack
output ([decoding.md](../patch-rom/decoding.md)). The reads only make sense this
way. For example, the DCO2 PW compiler tests bits 0 and 2 of `+$12`, and param 18
is the 3-bit DCO2 noise/wave/pulse enable.

| Dest code (`$7220`) | Parameter (patch #) | Compiler | Primitive (store) | Voice-block ptr | Channel address | CEM3396 input (pin) |
|---|---|---|---|---|---|---|
| 3 | DCO1 waveshape (10) | `$9633` | `$8950` (`$8993`) | `+$79` | `$1000 + n×$10` | Waveshape A (2) |
| 2 | DCO1 pulse width (11) | `$9660` | `$89B8` (`$89E0`) | `+$7B` | `$1006 + n×$10` | Pulse width A (5) |
| 2, pulse off | (DCO1 pulse disabled) | `$9660` | `$89AF` (`$89E0`) | `+$95` | `$1086 + n×$10` | see note below |
| 6 | DCO2 waveshape (15) | `$975B` | `$8B67` (`$8BAA`) | `+$81` | `$100E + n×$10` | Waveshape B (10) |
| 5 | DCO2 pulse width (16) | `$9788` | `$8BCC` (`$8BF4`) | `+$83` | `$100A + n×$10` | Pulse width B (7) |
| 5, pulse off | (DCO2 pulse disabled) | `$9788` | `$8BC3` (`$8BF4`) | `+$97` | `$108A + n×$10` | see note below |
| 7 | DCO mix (20) | `$98E5` | `$8CD6` (`$8CDE`) | `+$8B` | `$1160 + n×2` | Balance (14) |
| 8 | VCF FM amount (30) | `$9846` | `$8C95` (`$8C9D`) | `+$87` | `$108C + n×$10` | Modulation amount (11) |
| 9 | VCF frequency (26) | `$97D7` | `$8C0A` (`$8C70`) | `+$85` | `$1102 + n×$10` | Filter frequency (20) |
| 10 | VCF resonance (27) | `$9866` | `$8CB5` (`$8CBD`) | `+$89` | `$106C + n×2` | Resonance (15) |
| 11 | VCA1 (31) | `$9907` | `$8CFA` (`$8D02`) | `+$8D` | `$1004 + n×$10` | Linear gain (22) *(inferred)* |
| 12 | VCA2 (envelope; no static param) | `$992F` | `$8D1B` (`$8D45`) | `+$8F` | `$1008 + n×$10` | Log gain (1) *(inferred)* |

Pitch (dest 1, DCO1: compiler `$95AB` → `$8765`; dest 4, DCO2: compiler `$96A5`
→ `$89F6`) does not use the DAC; it loads the voice's 8253 counters (`+$75`/`+$91`
for DCO1, `+$7D`/`+$93` for DCO2, from the `$8220` table). See
[voice-architecture.md](voice-architecture.md).

That accounts for **all ten DAC-driven CEM3396 inputs**. The chip's eleventh
control input, **wave select** (pin 6), is a four-level input that the datasheet
suggests driving from two logic bits (its Figure 2); it is not on any of these
channels. The firmware's per-DCO wave-enable bits are accumulated into
`$7213`/`$7214` and written to `$107E` (`$9600`, `$9728`), the likely path, not
yet confirmed against the schematic.

How the parameter-to-pin column was established:

- **Waveshape, PW, mix, FM, cutoff, resonance** are each the only input with that
  function, so the patch parameter fixes the pin. DCO1 = converter A and DCO2 =
  converter B is the natural reading, not yet checked against the schematic.
- **VCA1 vs VCA2 → linear vs log** follows voice-architecture.md; the code shows
  only that VCA2 (`$8D1B`) is scaled by `+$A5` and capped at `+$A7`, not which
  taper it drives.

### What the primitives' arithmetic confirms

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
  flag to a per-DCO latch, **`$1C00 + n` (DCO1, `+$77`)** and **`$1C80 + n`
  (DCO2, `+$7F`)**, ordered before or after the DAC strobe depending on the
  direction of the switch. That is the datasheet's Rt range switch. The per-range
  pitch offsets are `+$39/+$3B` and `+$3D/+$3F`, defaulted at `$DD88`.

### Per-voice calibration tables (cutoff and resonance)

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

### Notes on the address layout

- Eight channels sit at **`$1000 + n×$10`** offsets `0, 4, 6, 8, A, E` and
  `$80 + 6, A, C`. Cutoff is at `$1100 + n×$10 + 2`. Resonance and mix use a
  **stride of 2** (`$106C + 2n`, `$1160 + 2n`) and live in the `$8220` table rather
  than the `$7207` arithmetic. So they sit on a different mux bank from the
  other eight.
- **Pulse off uses a different address.** When a DCO's pulse is disabled, the
  compiler emits a zero-value primitive (`$89AF`/`$8BC3`) that waits about 20 loops
  and writes to the PW offset **+`$80`** (`$1086`/`$108A`) instead of the normal PW
  channel. The datasheet recommends a slightly *negative* Vpw (−50 to −500 mV)
  to guarantee the pulse is off. That suggests the A7 alias reaches the same
  pin through a negative offset, but the schematic would have to confirm it.
- **The boot write to `$1008` mutes the voices.** `FUN_81e4` writes raw
  `$8000` to `$1008 + n×$10`, repeating 50 times (`$7222 = $32`). Every primitive
  flips the top bit (`EORA #$80`) before storing, so raw `$8000` is computed value
  **0**. The channel is VCA2, so this sets all six voices' output VCAs to zero at
  power-up (an earlier revision called it a "mid-scale settle").

## Correction: `FUN_8765` is the *timer* write, not the DAC

An earlier revision documented a "DAC write protocol" using `FUN_8765` — writing
two bytes to the **same** address then toggling `+$91`. That turned out to be the
**8253 pitch write**, not a DAC write: writing LSB-then-MSB to one address is the
8253 counter-load, `+$75`/`+$91` are the voice's timer counter/control (from the
`$8220` table), and it's driven by the `$A652` note→divider table
(voice-architecture.md / timing-clocks.md). So that sequence belongs to *pitch*,
not the DAC.

Note the `$8220` table caches **both** kinds of target per voice: the two 8253
counters (`$0000`-region, pitch) *and* DAC channels (`$106x`/`$116x`), alongside
panel latch addresses.

## The DAC-CV write — isolated

The per-parameter DAC write is done by a **family of twelve destination primitives
at `$8950`–`$8D1B`** (ten CVs plus the two pulse-off variants), the analog-CV
siblings of the pitch primitive `FUN_8765`. Each one loads a different **cached
channel pointer** from the voice block (`LDX <$79`, `<$7B`, `<$81`, `<$83`,
`<$85`, `<$87`, `<$89`, `<$8B`, `<$8D`, `<$8F`, `<$95`, `<$97`, set at boot,
`$80D8–$8146`) and writes the computed value to
that channel, strobing **`$1800`** to select the mux / S&H target, then threads on
(`PULU PC`). E.g. `$8991`:

```
8991  LDX <$79        ; this voice's DAC channel pointer ($1000 + n*$10 + k)
8993  STB 1,X         ; value bytes to the channel
8995  STA $1800       ; strobe the mux / S&H channel select
8998  STA ,X+
...   PULU PC         ; next primitive
```

So the write is **value → channel + `$1800` mux-select strobe** (unlike the pitch
path, which loads the 8253 counter). Each primitive writes the value twice, low
byte with bit 2 set and then with bit 2 clear, so bit 2 of the low byte acts as
a strobe. The value is shifted left two places and its top bit is flipped
(`EORA #$80`), which converts a signed computed value into the DAC's offset-binary
input. Which primitive drives which parameter is the table in
[Per-voice channel map](#per-voice-channel-map). Note `$1800` is thus **written**
(mux select) here as well as **read** (panel) elsewhere, a refinement to the I/O
map.

## Failure points

The DAC, the **4053** next to it, and the pair of **4051s** behind each voice are
the classic field failures (one stuck/wandering parameter or voice). The CEM3396s
themselves are usually fine. (Community/service literature.)

## Open items

- Confirm the AM6012 part and the exact `$1000`-block register decode against the
  schematic: the address-bit meaning of the `+$80` pulse-off alias, the stride-2
  resonance/mix bank, and the `$107E` wave-select write.
- Confirm DCO1 = converter A and VCA1 = linear-gain pin against the schematic.
- Resolve the `$2018+` voice-status lines (see voice-architecture.md).
