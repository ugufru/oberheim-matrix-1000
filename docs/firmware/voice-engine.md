# Voice engine (per-voice CV computation & scan-out)

How the firmware turns a patch into the stream of control voltages that drive the
six CEM3396 voices. This is the execution machinery; the *meaning* of the
modulation routings it runs is the modulation-matrix doc (#9), and the mapping of
each DAC channel to a synth parameter is the DAC/voice hardware doc (#13). From
the **v1.11** ROM.

## Key convention: DP = the voice page

During per-voice processing the firmware sets the 6809 **direct-page register to
the voice block's page** (`$60, $63, $66, $69, $6C, $6F` for voices 0–5). Every
`voice*$100 + offset` access in the decompiler output is therefore a one-byte
direct-page operation on *the current voice's* block. This is why the voice
blocks are page-aligned at `$6000 + n×$300` (see [ram-map](ram-map.md)) and is
the convention behind the whole engine. (Resolves the DP open question in the
RAM map.)

## Two paths: rebuild vs execute

The engine separates **compiling** a voice's modulation program from **running**
it — the structure that GliGli's v1.16 CFW sped up ("parameter changes that need
a modulation-matrix rebuild").

```
  rebuild (on patch / parameter change)        execute (every tick)
  ───────────────────────────────────          ────────────────────
  FUN_8EBA  loop voices (mask $7217)            FUN_85E7 tick engine
    set DP = voice page                           per voice: step envelopes
    call $720F  (= FUN_8F34)                       call FUN_875A  ← run program
      run ~26 element routines                       executes the cached
      cache routine-pointer list                     routine list → CVs
      into voice block +$41..+$6F                   write DAC channels
```

### Rebuild — `FUN_8F34` (per-voice, via `$720F`)

For the current voice (DP = its page) it runs a fixed sequence of ~26 element
routines (`FUN_9266`, `FUN_8FE9`, `FUN_90FA`, `FUN_9866`, …) — one per modulation
source/destination element — and stores each element's work pointer into a
table inside the voice block at offsets **`+$41, +$43, … +$6F`** (stepping by 2).
Two small combinator stubs at **`$8760`** (OR/accumulate) and **`$8765`** (clear)
are wired in as list heads (`puVar1 = $8760`). The net result is a per-voice
**compiled modulation program**: an ordered list of routine pointers cached in
the block, ready to execute cheaply. Enumerating which element routine is which
source/destination is #9's job.

### Execute — `FUN_875A` (per-voice, each tick)

```
875a: (* **(DP*$100 + $71))()      ; call through the voice block's program head
```

`FUN_875A` calls through the pointer at **voice `+$71`**, which heads the compiled
list built during rebuild. Running the list computes the voice's current control
values and emits them. Because the list is just routine pointers (threaded code),
per-tick cost is low — no matrix re-evaluation, just "run the program."

### Modulator state is per-voice

The modulators are not shared. Each LFO/envelope/ramp primitive keeps its state
**in the voice block**: e.g. the LFO runtime primitive `$A0CF` accumulates its
phase with `ADDD 0x2,Y / STD 0x2,Y` where `Y` is the per-voice work area
(`voice_block + $21C`, baked in by the compiler `FUN_90FA`), and uses DP-relative
(`<$0B`, DP = voice page) scratch. So all six voices run **independent** LFOs,
envelopes and ramps — the `$7A3B…` tables the tick engine reads are *static*
key/velocity curves (no runtime writers), not shared modulator outputs. (This is
what makes per-voice-different sounds tractable — see the multitimbral note in
`docs/architecture.md`.)

## CV scan-out to the DAC

The computed values are written to the voice's **DAC / sample-and-hold channels**
at `$1000 + n×$10`, whose addresses are pre-cached in the voice block at
`+$79, +$7B, +$81, …` (built in `vec_RESET`; see ram-map). The single AM6012 DAC
is multiplexed, so "writing a CV" is: select the channel (via the cached address)
and store the value; the hardware sample-and-hold for that parameter/voice holds
it until the next refresh. Which `+$10 + k` channel is pitch vs PW vs cutoff vs
VCA is resolved in #13.

## The tick's fast per-voice work — `FUN_85E7`

Beyond invoking the compiled program, the tick engine itself does the cheap,
must-happen-every-tick stepping directly on the voice block (DP-relative):

- envelope/phase advance (fields `+$14…+$23`),
- pitch/portamento glide toward target (`+$15` → `+$1B`, `+$1D/+$1F`),
- round-robin hand-off of one voice's slow global modulators per tick (via
  `$7228`), spreading load across ticks.

Detailed field semantics are in [ram-map](ram-map.md); the envelope/LFO maths is
shared with #9.

## Why this design

Splitting compile from execute is what lets a 2 MHz 6809 run a 20-destination
modulation matrix for six voices in real time: the expensive routing decisions
happen once per change, and each tick just runs straight-line threaded code and
stores to the DAC. It also explains the original firmware's sluggishness on live
parameter edits (every edit forces a rebuild) and why the CFW work targeted that
path.

## Open items

- Map each of the ~26 element routines (`FUN_9266`…) to its modulation
  source/destination (#9).
- Map each `$1000 + n×$10 + k` DAC channel to its synth parameter (#13).
- Confirm exactly when a rebuild (`FUN_8EBA`) is triggered vs. the per-tick
  execute path, and the cost of each.
