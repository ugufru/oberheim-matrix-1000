# Modulation matrix (compile & evaluate)

The Matrix-1000's signature feature is its modulation matrix: ~20 routable
sources into ~32 destinations, plus the fixed front-panel routings. This doc is
about *how the firmware realises it*. The short version, building on the
[voice engine](voice-engine.md) (#8): **the matrix is compiled to threaded code,
not interpreted.** From the **v1.11** ROM. The exact patch byte layout of the
routings is the patch parameter map's job (#16); here we cover the engine.

## The big idea: a matrix-to-threaded-code compiler

When a patch (or an edited parameter) is applied, the rebuild path
(`FUN_8EBA → FUN_8F34`, #8) runs ~26 **element routines**, one per modulation
destination/stage. Each element routine:

1. reads its slice of the **active patch buffer** (`_DAT_7218`, = the patch
   pointer `$7A19`) at fixed offsets — e.g. `+$2A`, `+$3A`, `+$42` — i.e. that
   destination's amount/source/parameter bytes;
2. checks an **enable bit** (`if ((*_DAT_7218 & 2)==0) return;`) and bails if the
   destination is inactive — so nothing is emitted for unused routings;
3. **emits a chain of primitive-routine addresses** into the per-voice program
   buffer (the build cursor `_DAT_720B` / `in_Y`), choosing primitives based on
   the patch settings.

The emitted addresses are entries in a **primitive library** at roughly
`$A000–$A6xx`. Examples seen being written: `$A0CF`, `$A0F0`, `$A380`, `$A3F5`,
`$A475`, `$A4D5`, `$A4E5`, `$A511`, `$A540`, `$A590`, `$A5EE`, `$A638`. Each is a
small routine that does one step — load a value, add a modulation source, scale,
clamp, or write a CV to a DAC channel.

The result is a per-voice **compiled program**: a straight-line list of primitive
calls with operands, cached in the voice block, that `FUN_875A` executes every
tick (#8). No routing decisions happen at tick time — they were baked in at
compile time.

### Static vs modulated fast paths

Throughout the element routines a flag `DAT_7221` selects between two primitive
variants — e.g. `$A0F0` vs `$A0D1`, `$A380` vs `$A376`. The helper `FUN_9958`
(with a source selector in `DAT_7202`) decides whether a given destination has an
active modulation source: if not, a cheaper "load constant" primitive is emitted;
if so, a primitive that adds the source each tick. This is how an inactive
routing costs nothing at run time.

## Element routine anatomy (example: `FUN_9266`)

A representative oscillator-destination compiler:

- gated by `*_DAT_7218 & 2` (destination active?);
- reads oscillator params at `_DAT_7218 + $3A` / `+$42`;
- emits a base primitive chosen from a table at `$A475` by waveform/sync bits
  (`$A475/$A4D5/$A4E5`);
- makes **four** `FUN_9958` calls with `DAT_7202 = $40` — i.e. **four modulation
  taps** for this destination — each emitting a source-add primitive
  (`$A511/$A540/$A590/$A5EE`) when that tap is routed;
- terminates the chain with `$A638` (or `$A62E` when modulated).

`FUN_90FA` is the same shape for another destination (params at `+$2A`,
primitives `$A0CF/$A0F0/$A380/$A3F5`). The ~26 routines differ only in which
patch bytes they read and which primitive family they draw from.

> Mapping each element routine to a *named* destination (DCO1 freq / PW, DCO2,
> VCF cutoff / resonance, VCA, FM, etc.) and each `$Axxx` primitive to its
> operation is in progress; the firm result is the **mechanism** above. The
> specific destination names below are inferred from the patch offsets they read
> and will be confirmed against the patch parameter map (#16).

## A run-time primitive: pitch (`FUN_8765`)

One of the executed primitives, to show what the compiled program actually does
per tick for the DCO pitch destination:

- takes the voice's pitch accumulator (`DP+$19`), looks up a **frequency table**
  at `$A652`/`$A654` (note → oscillator code), applies portamento/glide and
  modulation offsets (`DP+$39/$3D`);
- writes the 12-bit result to the voice's **DAC channel** (pointer at `DP+$75`)
  as two byte stores, toggling the **mux/S&H strobe latch** (pointer at `DP+$91`,
  values `^$0E` / `^$02`) so the value lands in this voice's pitch sample-and-hold;
- folds in the **autotune** reference compare (constants `$0488`, `$05DC`,
  references at `DP+$A0/$A2`) — i.e. tuning correction happens inside the pitch
  primitive (ties to #12).

So a "destination" at run time = compute value → store to DAC channel → strobe
the right S&H. The DAC-channel ↔ parameter mapping is finalised in #13.

## Why compile?

A 2 MHz 6809 cannot re-walk a 20-routing matrix for six voices ~50×/second. By
compiling each patch into per-voice threaded code, the per-tick cost collapses to
running a short straight-line list. The price is that **any parameter edit forces
a recompile** (all ~26 element routines, per voice) — directly the sluggishness
the Nordcore/GliGli CFWs attacked (GliGli: "faster processing of parameter
changes that need a modulation-matrix rebuild").

## Open items

- Name each of the ~26 element routines → destination, and tabulate the `$Axxx`
  primitive library (op per address).
- Map the patch-buffer offsets the routines read (`+$2A`, `+$3A`, `+$42`, …) to
  the patch parameter map (#16).
- Confirm the source-selection encoding in `FUN_9958` / `DAT_7202` against the
  matrix routing bytes.
