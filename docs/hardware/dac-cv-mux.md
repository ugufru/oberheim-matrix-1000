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

## Per-voice channel layout

DAC/S&H channels are addressed at **`$1000 + n×$10`** for voice `n`, with a fixed
set of sub-offsets per parameter. The firmware caches these channel addresses
into each voice block at boot (`vec_RESET`), so scan-out is a few indexed stores
rather than address arithmetic. Examples from the init (voice-block offset →
channel):

- `+$79 → $1000 + n×$10`, `+$7B → +$06`, `+$8D → +$04`, `+$8F → $1008 + n×$10`,
  `+$81 → +$0E`, `+$83 → +$0A`, plus shared destinations at `+$86/$8A/$102` in the
  `$1080/$1100` range.

`FUN_81e4` (boot) writes mid-scale `$8000` to `$1008 + n×$10` for all six voices —
a DAC/voice settle that confirms one channel per voice at that stride.

> The exact channel-offset → synth-parameter map (which sub-offset is cutoff vs
> PW vs VCA) is partially recovered; completing it is the remaining detail here,
> cross-referenced with the parameter model (#16).

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

The per-parameter DAC write is done by a **family of ~10 destination primitives at
`$8991`–`$8D41`**, the analog-CV siblings of the pitch primitive `FUN_8765`. Each
one loads a different **cached channel pointer** from the voice block (`LDX <$79`,
`<$7B`, `<$81`, `<$83`, `<$85`, `<$87`, `<$8D`, `<$8F`, `<$95`, `<$97` — the
`$1000`-based pointers set at boot, `$80DE–$8146`) and writes the computed value to
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
path, which loads the 8253 counter). The ten channels are `$1000 + n*$10 + {0,4,6,
8,A,E}` plus shared destinations in the `$1080/$1100` range (the pointer
assignments in `vec_RESET`).

**Remaining follow-up:** *which* primitive drives *which* named parameter (filter
freq vs resonance vs VCA1/VCA2 vs waveshape/PW/balance) — trace which destination
compiler (element routine, #9) emits each `$89xx–$8Dxx` address. The primitives and
the write mechanism are now nailed; the channel→parameter labels are the last mile
(with #13). Note `$1800` is thus **written** (mux select) here as well as **read**
(panel) elsewhere — a refinement to the I/O map.

## Failure points

The DAC, the **4053** next to it, and the pair of **4051s** behind each voice are
the classic field failures (one stuck/wandering parameter or voice). The CEM3396s
themselves are usually fine. (Community/service literature.)

## Open items

- Complete the channel-offset → parameter map (#16 cross-reference).
- Confirm the AM6012 part and the exact `$1000`-block register decode against the
  schematic.
- Resolve the `$2018+` voice-status lines (see voice-architecture.md).
